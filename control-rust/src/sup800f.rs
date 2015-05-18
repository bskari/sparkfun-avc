/// Functions for communicating with the SUP800F GPS module.
use std::io::{BufRead, Error, ErrorKind, Result, Write};
use std::mem::transmute;


/// Returns a single message.
fn get_message(serial: &mut BufRead) -> Result<Vec<u8>> {
    let mut byte = [0u8; 1];
    let mut length_buffer = [0u8; 2];
    // Keep consuming bytes until we see the header message
    loop {
        let mut result = serial.read(&mut byte);
        match result {
            Ok(_) => (),
            Err(err) => return Err(err),
        }
        if byte[0] != 0xA0 {
            continue;
        }
        result = serial.read(&mut byte);
        match result {
            Ok(_) => (),
            Err(err) => return Err(err),
        }
        if byte[0] != 0xA1 {
            continue;
        }
        result = serial.read(&mut length_buffer);
        match result {
            Ok(_) => (),
            Err(err) => return Err(err),
        }
        let payload_length: u16 = u16::from_le( unsafe { transmute(length_buffer) } );
        // Sanity check
        if payload_length > 1024 || payload_length < 4 {
            return Err(
                Error::new(
                    ErrorKind::Other,
                    format!(
                        "Invalid payload length: {}",
                        payload_length).to_string()));
        }
        let total_length: usize = (payload_length + 4) as usize;
        let mut message: Vec<u8> = Vec::with_capacity(total_length);
        unsafe { message.set_len(total_length) };
        match serial.read(&mut message.as_mut_slice()[4..]) {
            Ok(bytes_read) => if bytes_read != payload_length as usize {
                return Err(
                    Error::new(
                        ErrorKind::Other,
                        format!(
                            "Wrong number of bytes read: {}, expected {}",
                            bytes_read,
                            payload_length).to_string()));
            },
            Err(err) => return Err(err),
        }
        message[0] = 0x0A;
        message[1] = 0x0A;
        message[2] = length_buffer[0];
        message[3] = length_buffer[1];
        return Ok(message);
    }
}


/// Switches to the NMEA message mode.
fn switch_to_nmea_mode(serial: &mut Write) -> Result<()> {
    _change_mode(serial, 1)
}


/// Switches to the binary message mode.
fn switch_to_binary_mode(serial: &mut Write) -> Result<()> {
    _change_mode(serial, 2)
}


/// Change reporting mode between NMEA messages or binary (temperature, accelerometer and
/// magnetometer) mode.
fn _change_mode(serial: &mut Write, mode: u8) -> Result<()> {
    // message id, 9 = configure message type
    let payload: Vec<u8> = vec![9, mode, 0];
    let message = _format_message(&payload);
    match serial.write(&message.into_boxed_slice()) {
        Ok(_) => (),
        Err(err) => return Err(err),
    }
    // TODO: See if the mode changed successfully
    Ok(())
}


/// Formats a message for the SUP800F, including adding a length designator and a checksum.
fn _format_message(payload: &Vec<u8>) -> Vec<u8> {
    let checksum = payload.iter().fold(0u8, |part, byte| part ^ byte);
    let mut vector: Vec<u8> = vec![0xA0, 0xA1];
    let length: u16 = payload.len() as u16;
    let payload_bytes: [u8; 2] = unsafe { transmute(length.to_be()) };
    vector.push_all(&payload_bytes);
    vector.push_all(payload);
    vector.push(checksum);
    vector.push_all(&[0x0D, 0x0A]);
    vector
}


#[cfg(test)]
mod tests {
    use std::io::Cursor;
    use std::mem::transmute;
    use super::{get_message, _format_message};

    #[test]
    fn test_format_message() {
        {
            let empty_message: Vec<u8> = Vec::new();
            let formatted = _format_message(&empty_message);
            let length = formatted.len();
            assert!(formatted[length - 1] == '\n' as u8);
            assert!(formatted[length - 2] == '\r' as u8);
            // The payload ends in length, checksum, \n, \r
            let slice: [u8; 2] = [formatted[length - 5], formatted[length - 3]];
            let payload_length: u16 = unsafe { transmute(slice) };
            assert!(payload_length == 0);
        }
        {
            let byte: u8 = 0x45;
            // We'll duplicate bytes because they should be cancelled out in the xor checksum
            let message: Vec<u8> = vec![0x17, 0xA1, 0xA1, byte, 0x17];
            let formatted = _format_message(&message);
            let length = formatted.len();
            assert!(formatted[length - 1] == '\n' as u8);
            assert!(formatted[length - 2] == '\r' as u8);
            // The payload ends in length, checksum, \n, \r
            let slice: [u8; 2] = [formatted[length - 5], formatted[length - 3]];
            let payload_length: u16 = unsafe { transmute(slice) };
            println!("{} == {}", payload_length, message.len());
            assert!(payload_length == message.len() as u16);
            // Checksum
            assert!(formatted[length - 3] == byte);
        }
    }

    #[test]
    fn test_get_message() {
        let mut buffer: Vec<u8> = vec![
            // Binary message
            0xA0, 0xA1, 0x00, 0x22, 0xCF, 0x01, 0xBD, 0x4F, 0xE1, 0x54, 0xBE, 0x15, 0xE9, 0xE2, 0x3F, 0x6F, 0x3C, 0xB4, 0xC0, 0xC5, 0x9D, 0x2A, 0x40, 0x79, 0x84, 0x08, 0x40, 0xCE, 0xFA, 0xB0, 0x00, 0x01, 0x85, 0xB1, 0x41, 0xF1, 0x99, 0x9A, 0xB4, 0x0D, 0x0A,
        ];
        let length = buffer.len();

        let empty_message: Vec<u8> = Vec::new();
        let mut formatted = _format_message(&empty_message);
        buffer.push_all(&formatted[..]);

        let first_message = match get_message(&mut Cursor::new(buffer)) {
            Ok(message) => message,
            Err(err) => panic!("No message extracted"),
        };
        assert!(first_message.len() == length);
    }
}

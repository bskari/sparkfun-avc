/**
 * FFI bindings for the Termios library. There is a Termios crate but I had trouble getting it to
 * work. I couldn't get the example code to work and I'm not sure how you would call the different
 * functions anyway.
 */

extern crate enum_primitive;
extern crate libc;

use std::mem::transmute;
use std::os::unix::prelude::AsRawFd;
use num::FromPrimitive;


pub trait Termio {
    fn set_speed(&self, speed: Speed) -> Result<i32, i32>;
    fn get_speed(&self) -> Result<Speed, i32>;
    fn drain(&self) -> Result<i32, i32>;
    fn drop_input(&self) -> Result<i32, i32>;
    fn drop_output(&self) -> Result<i32, i32>;
    fn drop_input_output(&self) -> Result<i32, i32>;
    fn input_buffer_count(&self) -> Result<i32, i32>;
    fn errno(&self) -> i32;
}
impl<T> Termio for T where T: AsRawFd {
    fn set_speed(&self, speed: Speed) -> Result<i32, i32> {
        let fd = self.as_raw_fd();
        let mut config = CTermios::new();
        if unsafe { tcgetattr(fd, &mut config) } < 0 {
            return Err(self.errno());
        }
        if unsafe { cfsetspeed(&mut config, speed as u32) } < 0 {
            return Err(self.errno());
        }
        if unsafe { tcsetattr(fd, TcSetattrOptions::TCSANOW as i32, &mut config) } < 0 {
            return Err(self.errno());
        }
        Ok(0)
    }

    fn get_speed(&self) -> Result<Speed, i32> {
        let fd = self.as_raw_fd();
        let mut config = CTermios::new();
        if unsafe { tcgetattr(fd, transmute(&mut config)) } < 0 {
            return Err(self.errno());
        }
        let getospeed = unsafe {
            cfgetospeed(&mut config)
        };
        match Speed::from_u32(getospeed) {
            Some(speed) => Ok(speed),
            None => Err(1) // TODO: I'm not too sure what to do here
        }
    }

    fn drain(&self) -> Result<i32, i32> {
        let fd = self.as_raw_fd();
        if unsafe { tcdrain(fd) } < 0 {
            Err(self.errno())
        } else {
            Ok(0)
        }
    }

    fn drop_input(&self) -> Result<i32, i32> {
        let fd = self.as_raw_fd();
        if unsafe { tcflush(fd, TcFlushOptions::TCIFLUSH as i32) } < 0 {
            Err(self.errno())
        } else {
            Ok(0)
        }
    }

    fn drop_output(&self) -> Result<i32, i32> {
        let fd = self.as_raw_fd();
        if unsafe { tcflush(fd, TcFlushOptions::TCOFLUSH as i32) } < 0 {
            Err(self.errno())
        } else {
            Ok(0)
        }
    }

    fn drop_input_output(&self) -> Result<i32, i32> {
        let fd = self.as_raw_fd();
        if unsafe { tcflush(fd, TcFlushOptions::TCIOFLUSH as i32) } < 0 {
            Err(self.errno())
        } else {
            Ok(0)
        }
    }

    #[allow(unused_mut)]
    fn input_buffer_count(&self) -> Result<i32, i32> {
        let fd = self.as_raw_fd();
        let buffer_size = unsafe {
            // I don't know if this mut annotation is necessary with transmute; will the compiler
            // optimize the value out?
            let mut size: i32 = 0;
            let result = ioctl(fd, IoCtlOptions::FIONREAD as i32, transmute(&size));
            if result < 0 {
                result
            } else {
                size
            }
        };
        if buffer_size < 0 {
            Err(self.errno())
        } else {
            Ok(buffer_size)
        }
    }

    fn errno(&self) -> i32 {
        // TODO: Get the errno
        0
    }
}


#[allow(non_camel_case_types)]
type cc_t = u8;
#[allow(non_camel_case_types)]
type tcflag_t = u32;
#[allow(non_camel_case_types)]
type speed_t = u32;

#[repr(C)]
struct CTermios
{
    c_iflag: tcflag_t,  // input mode flags
    c_oflag: tcflag_t,  // output mode flags
    c_cflag: tcflag_t,  // control mode flags
    c_lflag: tcflag_t,  // local mode flags
    c_line: cc_t,       // line discipline
    c_cc: [cc_t; 32],   // control characters
    c_ispeed: speed_t,  // input speed
    c_ospeed: speed_t,  // output speed
}
impl CTermios {
    fn new() -> CTermios {
        CTermios {
            c_iflag: 0,
            c_oflag: 0,
            c_cflag: 0,
            c_lflag: 0,
            c_line: 0,
            c_cc: [0u8; 32],   // control characters
            c_ispeed: 0,  // input speed
            c_ospeed: 0,  // output speed
        }
    }
}

#[allow(dead_code)]
pub enum ControlCharacters {
    VINTR = 0,
    VQUIT = 1,
    VERASE = 2,
    VKILL = 3,
    VEOF = 4,
    VTIME = 5,
    VMIN = 6,
    VSWTC = 7,
    VSTART = 8,
    VSTOP = 9,
    VSUSP = 10,
    VEOL = 11,
    VREPRINT = 12,
    VDISCARD = 13,
    VWERASE = 14,
    VLNEXT = 15,
    VEOL2 = 16,
}

#[allow(dead_code)]
pub enum IflagBits {
    IGNBRK = 0000001,
    BRKINT = 0000002,
    IGNPAR = 0000004,
    PARMRK = 0000010,
    INPCK = 0000020,
    ISTRIP = 0000040,
    INLCR = 0000100,
    IGNCR = 0000200,
    ICRNL = 0000400,
    IUCLC = 0001000,
    IXON = 0002000,
    IXANY = 0004000,
    IXOFF = 0010000,
    IMAXBEL = 0020000,
    IUTF8 = 0040000,
}

#[allow(dead_code)]
pub enum OflagBits {
    OPOST = 0000001,
    OLCUC = 0000002,
    ONLCR = 0000004,
    OCRNL = 0000010,
    ONOCR = 0000020,
    ONLRET = 0000040,
    OFILL = 0000100,
    OFDEL = 0000200,
    VTDLY = 0040000,
    //VT0 = 0000000,
    //VT1 = 0040000,
}

#[allow(dead_code)]
enum_from_primitive! {
pub enum Speed {
    B0 = 0000000,
    B50 = 0000001,
    B75 = 0000002,
    B110 = 0000003,
    B134 = 0000004,
    B150 = 0000005,
    B200 = 0000006,
    B300 = 0000007,
    B600 = 0000010,
    B1200 = 0000011,
    B1800 = 0000012,
    B2400 = 0000013,
    B4800 = 0000014,
    B9600 = 0000015,
    B19200 = 0000016,
    B38400 = 0000017,
    B57600 = 0010001,
    B115200 = 0010002,
    B230400 = 0010003,
    B460800 = 0010004,
    B500000 = 0010005,
    B576000 = 0010006,
    B921600 = 0010007,
    B1000000 = 0010010,
    B1152000 = 0010011,
    B1500000 = 0010012,
    B2000000 = 0010013,
    B2500000 = 0010014,
    B3000000 = 0010015,
    B3500000 = 0010016,
    B4000000 = 0010017,
}
}

#[allow(dead_code)]
pub enum CflagBits {
    CS5 = 0000000,
    CS6 = 0000020,
    CS7 = 0000040,
    CS8 = 0000060,
    CSTOPB = 0000100,
    CREAD = 0000200,
    PARENB = 0000400,
    PARODD = 0001000,
    HUPCL = 0002000,
    CLOCAL = 0004000,
}

#[allow(dead_code)]
enum LflagBits {
    ISIG = 0000001,
    ICANON = 0000002,
    ECHO = 0000010,
    ECHOE = 0000020,
    ECHOK = 0000040,
    ECHONL = 0000100,
    NOFLSH = 0000200,
    TOSTOP = 0000400,
}

#[allow(dead_code)]
enum TcSetattrOptions {
    TCSANOW = 0,
    TCSADRAIN = 1,
    TCSAFLUSH = 2,
}

#[allow(dead_code)]
enum TcFlushOptions {
    TCIFLUSH = 0,
    TCOFLUSH = 1,
    TCIOFLUSH = 2,
}

enum IoCtlOptions {
    FIONREAD = 21531,
}

#[allow(dead_code)]
extern {
    fn tcgetattr(fd: i32, termios_p: *mut CTermios) -> i32;
    fn tcsetattr(fd: i32, optional_actions: i32, termios_p: *mut CTermios) -> i32;
    fn tcsendbreak(fd: i32, duration: i32) -> i32;
    fn tcdrain(fd: i32) -> i32;
    fn tcflush(fd: i32, queue_selector: i32) -> i32;
    fn tcflow(fd: i32, action: i32) -> i32;
    fn cfmakeraw(termios_p: *mut CTermios) -> ();
    fn cfgetispeed(termios_p: *mut CTermios) -> speed_t;
    fn cfgetospeed(termios_p: *mut CTermios) -> speed_t;
    fn cfsetispeed(termios_p: *mut CTermios, speed: speed_t) -> i32;
    fn cfsetospeed(termios_p: *mut CTermios, speed: speed_t) -> i32;
    fn cfsetspeed(termios_p: *mut CTermios, speed: speed_t) -> i32;
    fn ioctl(fd: i32, request: i32, value: *mut i32) -> i32;
}

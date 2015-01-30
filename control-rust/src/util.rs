use std::cmp::min;

/**
 * Parse a float from a string. The Pi has an older version of rustc, and
 * the official method for parsing a float differ between that version and
 * nightly, so we have to do this manually.
 */
pub fn parse_float(float_str: &str) -> Option<f32> {
    // We parse the whole number and decimal part in halves to maintain
    // precision
    let negative = float_str.contains_char('-');
    println!("Negative {}", negative);
    let start: u32 = if negative { 1 } else { 0 };

    // We could multiply a value by 0.1 each time, but that introduces roundoff
    // errors very quickly, so we'll define a static array instead
    let divider: Vec<f32> = vec![1.0f32 /* dummy */, 0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001, 0.0000001];
    if float_str.contains_char('.') {
        let found = float_str.find('.');
        match found {
            Some(decimal_position) => {
                let integer_part_option = parse_int(float_str[start as uint..decimal_position]);
                match integer_part_option {
                    Some(integer_part) => {
                        println!("Upper = min({}, {})", float_str.len() - decimal_position + 1, divider.len() - 1);
                        let upper = min(float_str.len(), divider.len() - 1 + float_str.len());
                        let decimal_part_str = float_str[decimal_position + 1..upper];
                        println!("float_str {}, at {} = {}", float_str, decimal_position, float_str[decimal_position..decimal_position + 1]);
                        println!("Decimal part str = '{}'", decimal_part_str);
                        let decimal_part_option = parse_int(decimal_part_str);
                        match decimal_part_option {
                            Some(decimal_part) => {
                                let multiplier = divider[decimal_part_str.len()];
                                println!("multiplier {}", multiplier);
                                if negative {
                                    return Some(-integer_part as f32 + -decimal_part as f32 * multiplier);
                                }
                                return Some(integer_part as f32 + decimal_part as f32 * multiplier);
                            },
                            None => return None
                        }
                    },
                    None => return None
                }
            },
            None => return None  // This shouldn't happen
        }
    } else {
        match parse_int(float_str[start as uint..]) {
            Some(integer) => {
                if negative {
                    return Some(-integer as f32);
                }
                return Some (integer as f32);
            }
            None => return None,
        }
    }
}


/**
 * Parse an integer from a string. The Pi has an older version of rustc, and
 * the official method for parsing a float differ between that version and
 * nightly, so we have to do this manually.
 */
pub fn parse_int(int_str: &str) -> Option<i32> {
    println!("Parsing int {}", int_str);
    let mut value: i32 = 0;
    for letter in int_str.chars() {
        let digit_value = letter as i32 - '0' as i32;
        if digit_value > 9 || digit_value < 0 {
            return None;
        }
        value = value * 10 + digit_value;
    }
    Some(value)
}


mod tests {
    use super::parse_float;

    #[test]
    fn test_parse_float() {
        match parse_float("1") {
            Some(parsed) => assert!(parsed == 1.0f32),
            None => assert!(false),
        }
        match parse_float("-1")  {
            Some(parsed) => {
                println!("{}", parsed);
                assert!(parsed == -1.0f32);
            },
            None => assert!(false),
        }
        match parse_float("2.0") {
            Some(parsed) => assert!(parsed == 2.0f32),
            None => assert!(false),
        }
        match parse_float("-0.1")  {
            Some(parsed) => assert!(parsed == -0.1f32),
            None => assert!(false),
        }
        match parse_float("-2.0")  {
            Some(parsed) => assert!(parsed == -2.0f32),
            None => assert!(false),
        }
        match parse_float("123.456") {
            Some(parsed) => assert!(parsed == 123.456f32),
            None => assert!(false),
        }
        match parse_float("-123.456")  {
            Some(parsed) => assert!(parsed == -123.456f32),
            None => assert!(false),
        }
        match parse_float("0.1") {
            Some(parsed) => assert!(parsed == 0.1f32),
            None => assert!(false),
        }
        match parse_float("-0.0") {
            Some(parsed) => assert!(parsed == 0.0f32),
            None => assert!(false),
        }
    }
}

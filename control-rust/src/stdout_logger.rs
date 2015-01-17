use logger::Logger;

pub struct StdoutLogger;

impl Logger for StdoutLogger {
    fn debug(&self, message:&str) -> () {
        println!("{}", message);
    }

    fn info(&self, message:&str) -> () {
        println!("{}", message);
    }

    fn warning(&self, message:&str) -> () {
        println!("{}", message);
    }

    fn error(&self, message:&str) -> () {
        println!("{}", message);
    }

    fn critical(&self, message:&str) -> () {
        println!("{}", message);
    }
}

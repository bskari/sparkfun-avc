pub struct StdoutLogger;

// I want to write:
// impl Logger for StdoutLogger
// but it won't compile :(
impl StdoutLogger {
    pub fn debug(&self, message:&str) -> () {
        println!("{}", message);
    }

    pub fn info(&self, message:&str) -> () {
        println!("{}", message);
    }

    pub fn warning(&self, message:&str) -> () {
        println!("{}", message);
    }

    pub fn error(&self, message:&str) -> () {
        println!("{}", message);
    }

    pub fn critical(&self, message:&str) -> () {
        println!("{}", message);
    }
}

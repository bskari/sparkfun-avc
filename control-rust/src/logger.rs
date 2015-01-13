pub trait Logger {
    fn debug(&self, message:&str) -> ();
    fn info(&self, message:&str) -> ();
    fn warning(&self, message:&str) -> ();
    fn error(&self, message:&str) -> ();
    fn critical(&self, message:&str) -> ();
}

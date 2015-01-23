/**
 * Aggregates several loggers.
 */

use logger::Logger;

enum LogLevel {
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL,
}


struct MultiLogger {
    Vec<Box<Logger>> loggers;
    Vec<LogLevel> levels;
}


impl MultiLogger {
    fn add_logger(self, logger: Box<Logger>, level: LogLevel) {
        loggers.add(logger);
        levels.add(level);
    }

    fn log(self, message: &str, level: LogLevel) {
        // TODO Figure out how zip works
    }
}


impl Logger for MultiLogger {
    fn debug(&self, message: &str) -> ();
    fn info(&self, message: &str) -> ();
    fn warning(&self, message: &str) -> ();
    fn error(&self, message: &str) -> ();
    fn critical(&self, message: &str) -> ();
}

#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define COUNT_OF(x) ((sizeof(x)/sizeof(0[x])) / ((size_t)(!(sizeof(x) % sizeof(0[x])))))

int main(int argc, char* argv[]) {
    if (argc <= 1) {
        fprintf(stderr, "Usage: %s [command]\n", argv[0]);
        return -1;
    }
    argv[0] = "python";
    char path_buffer[512];
    strncpy(path_buffer, argv[1], COUNT_OF(path_buffer));
    int separator_index;
    for (separator_index = COUNT_OF(path_buffer) - 1; separator_index >= 0; --separator_index) {
        if (path_buffer[separator_index] == '/') {
            path_buffer[separator_index] = '\0';
            break;
        }
    }
    int success = chdir(path_buffer);
    if (success != 0) {
        return success;
    }
    return execv("/home/pi/.virtualenvs/sparkfun/bin/python", argv);
}

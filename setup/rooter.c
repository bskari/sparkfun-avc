#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define COUNT_OF(x) ((sizeof(x)/sizeof(0[x])) / ((size_t)(!(sizeof(x) % sizeof(0[x])))))

int main(int argc, char* argv[]) {
    if (argc <= 1) {
        fprintf(stderr, "Usage: %s [command]\n", argv[0]);
        exit(EXIT_FAILURE);
    }
    char* args[20];
    args[0] = "python";
    int i;
    for (i = 1; i < COUNT_OF(args) && argv[i] != NULL; ++i) {
        args[i] = argv[i];
    }
    if (i == COUNT_OF(args)) {
        fprintf(stderr, "Too many args\n");
        exit(EXIT_FAILURE);
    }
    int success = chdir("/home/pi/sparkfun-avc/");
    if (success != 0) {
        fprintf(stderr, "Unable to chdir\n");
        exit(EXIT_FAILURE);
    }
    return execv("/home/pi/.virtualenvs/sparkfun/bin/python", args);
}

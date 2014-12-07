#include <stdio.h>
#include <unistd.h>

int main(int argc, char* argv[]) {
    if (argc <= 1) {
        fprintf(stderr, "Usage: %s [command]\n", argv[0]);
        return -1;
    }
    argv[0] = "python";
    return execv("/home/bs/.virtualenvs/sparkfun/bin/python", argv);
}

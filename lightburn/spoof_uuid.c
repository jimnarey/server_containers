#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

int system(const char *command) {
    if (strstr(command, "blkid") || strstr(command, "lsblk")) {
        printf("/dev/sda: UUID=\"fake-uuid-1234\" TYPE=\"ext4\"\n");
        return 0;
    }
    int (*real_system)(const char *) = dlsym(RTLD_NEXT, "system");
    return real_system(command);
}

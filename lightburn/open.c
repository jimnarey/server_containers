#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

typedef int (*open_t)(const char *, int, ...);

typedef struct {
    const char *target;
    const char *spoof;
} FileMapping;



FileMapping mappings[] = {
    {"/sys/devices/virtual/dmi/id/bios_vendor", "/home/runuser/.bios_vendor"},
    {"/sys/devices/virtual/dmi/id/product_name", "/home/runuser/.product_name"},
    {"/sys/devices/virtual/dmi/id/product_serial", "/home/runuser/.product_serial"},
    {"/var/lib/dbus/machine-id", "/home/runuser/.machine-id"},
    {"/proc/cpuinfo", "/home/runuser/.cpuinfo"},
    {"/etc/os-release", "/home/runuser/.os-release"},
    {NULL, NULL}  // End marker
};

static open_t real_open = NULL;

void generate_random_string(char *str, size_t length) {
    const char charset[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    for (size_t i = 0; i < length; i++) {
        int key = rand() % (int)(sizeof(charset) - 1);
        str[i] = charset[key];
    }
    str[length] = '\0';
}

void create_spoof_files(void) {
    srand(time(NULL));
    for (FileMapping *mapping = mappings; mapping->spoof != NULL; ++mapping) {
        if (access(mapping->spoof, F_OK) == 0) {
            fprintf(stderr, "[INFO] Spoof file %s already exists, skipping creation\n", mapping->spoof);
            continue;
        }

        FILE *file = fopen(mapping->spoof, "w");
        if (file) {
            char random_string[21];
            generate_random_string(random_string, 20);
            fprintf(file, "%s\n", random_string);
            fclose(file);
            fprintf(stderr, "[INFO] Created spoof file %s\n", mapping->spoof);
        } else {
            fprintf(stderr, "[ERROR] Failed to create spoof file %s\n", mapping->spoof);
        }
    }
}

void init(void) __attribute__((constructor));
void init(void) {
    real_open = (open_t)dlsym(RTLD_NEXT, "open");
    if (!real_open) {
        fprintf(stderr, "[ERROR] Failed to find the real open function\n");
    } else {
        fprintf(stderr, "[INFO] Successfully hooked the open function\n");
    }
    create_spoof_files();
}

int open(const char *pathname, int flags, ...) {
    if (!real_open) {
        fprintf(stderr, "[ERROR] real_open is not initialized\n");
        return -1;
    }

    for (FileMapping *mapping = mappings; mapping->target != NULL; ++mapping) {
        if (strstr(pathname, mapping->target)) {
            fprintf(stderr, "[DEBUG] Spoofing access to %s with %s\n", pathname, mapping->spoof);
            return real_open(mapping->spoof, flags);
        }
    }

    return real_open(pathname, flags);
}

// To use
// gcc -shared -fPIC -o spoof_open.so spoof_open.c -ldl
// sudo -E LD_PRELOAD=./spoof_open.so blkid
//保留，c语言编写的启动器
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    FILE *fp = _popen("\".venv\\Scripts\\python.exe\" main.py 2>&1", "r");
    if (!fp) {
        perror("_popen");
        return 1;
    }

    char buf[4096];
    while (fgets(buf, sizeof(buf), fp)) {
        fputs(buf, stdout);
    }

    int code = _pclose(fp);
    printf("退出码: %d\n", code);
    return 0;
}
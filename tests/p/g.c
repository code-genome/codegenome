#include <stdio.h>
int g;
int* gp = &g;
int vec[]= {1,2,3};
int* intptr;

int f0(int a){
    int tmp = a;
    tmp = a + *gp;
    return tmp;
}

int f1(int a)
{
  int tmp;
  tmp = a + vec[0];
  return tmp;
}

void f2(int a){
  a = f0(a);
  printf("%d\n", a);
}

int main(int argc, char* argv[])
{
  int a = atoi(argv[1]);
  int x = f0(a);
  int y = f1(x);
  f2(y);
}

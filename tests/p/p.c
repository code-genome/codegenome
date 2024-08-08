#include<stdio.h>
#include <stdlib.h>

int g=1;
int* gp = &g;
int vec[]= {1,2,3};
int* intptr;

int gf1(int a){
    int tmp = a;
    tmp = a + *gp;
    intptr = &g;
    return tmp;
}

int gf2(int a)
{
  int tmp;
  tmp = a + vec[0];
  return tmp;
}

int f1(int a){
  int x;
  x = a + 32;
  return x;
}

int f2(int a){
  int local=31;
  local +=1;  
  local = a + local;
  return local;
}

int f3(int a){
  int local = a;  
  a = local;
  local = 30;
  a = a + local;
  a+=2;
  __asm__("xor %eax, %eax");
  __asm__("xor %eax, %eax");
  __asm__("xor %eax, %eax");
  return a;
}


int f4(int a){
  int l; int m; l = 30;
  m = l - 10;
  if (a>10){
    a = a+l;
    a+=2;
    return a;
  }
  else{
    __asm__("xor %eax, %eax");
    return a+m+12;
  }
}

int f5(int a){
  int l;  int m;  l = 30; m = 20;
  if (a>100){
    l = l + a;
    if(a>501){
      int tmp = 30-a;tmp = a+tmp;
      a = a + tmp+2;
      return a;
    }
    a = l + 2; l = m = a;
    return l;
  }
  else  if(a>10)
  {
    int tmp = a; a +=a; a = a - tmp;
    a = a + 32; return a;
  }else {
    int tmp = 30-a; tmp = tmp + a;
    tmp = tmp +2; a = a + tmp;
    return a;
  }
}

int f5_(int a){
  int l;
  int m;
  l = 30;
  m = 20;
  if (a>100){
    l = l + a;
    if(a>501){
      int tmp = 30-a;
      tmp = a+tmp;
      a = a + tmp+2;
      return a;
    }
    a = l + 2;
    l = m = a;
    return l;
  }
  else  if(a>10)
  {
    int tmp = a;
    a +=a;
    a = a - tmp;
    a = a + 32;
    return a;
  }else {
    int tmp = 30-a;
    tmp = tmp + a;
    tmp = tmp +2;
    a = a + tmp;
    return a;
  }
}

int main(int argc, char* argv[])
{
  int a = atoi(argv[1]);
  printf("%d\n%d\n%d",f1(a), f2(a),f3(a));
  a = f4(0);
  a = f5(0);
  a = gf1(0);
  a = gf2(0);
  return 0;
}

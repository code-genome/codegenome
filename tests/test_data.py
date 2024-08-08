global_c = """
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
  f0(a);
  return tmp;
}
"""

global_ir = """
@g = global i32 123, align 4
@gp = global i32* @g, align 8
@vec = global [3 x i32] [i32 1, i32 2, i32 3], align 4
@intptr = common global i32* null, align 8

define i32 @f0(i32 %a) {
  %1 = load i32*, i32** @gp, align 8
  %2 = load i32, i32* %1, align 4
  %3 = add nsw i32 %2, %a
  ret i32 %3
}

define i32 @f1(i32) {
  %2 = load i32, i32* getelementptr inbounds ([3 x i32], [3 x i32]* @vec, i64 0, i64 0), align 4
  %3 = add nsw i32 %2, %0
  ret i32 %3
}
"""

type_ir = """
%type1 =  type {
    i32,
    i32,
    double
}
%type2 = type {
    i32,
    i32,
    %type1
}

define i32* @f0(i32 %a) {

  %1 = alloca %type2
  %2 = getelementptr %type2, %type2* %1, i32 0, i32 1
  ret i32* %2
}
"""

externs_ir = """
declare i32 @printf(i8*, ...) local_unnamed_addr

define i32 @local_func(i32 %x) {
  ret i32 %x
  }

define i32 @f0(i32 %a, i8* %format) {
  %1 = call i32 @local_func(i32 %a)
  %2 = tail call i32 (i8*, ...) @printf(i8* %format)
  ret i32 %1
}
"""

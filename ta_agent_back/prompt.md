<role> 你是一名 C 语言入门课程的助教</role>
<task> 你的职责是辅助另一位主助教进行评分。你将收到一个作业问题和一份学生代码。请严格按照问题要求，对代码进行深入分析，给出一个建议的估分和检查报告，以供主助教参考</task>
反馈的重点： 你的核心任务是提供建设性的反馈。请明确指出学生哪里做得好，哪里有错误，以及哪些地方没有遵循题目要求
关键检查点 (用于生成反馈):
    功能正确性、遵循题目要求、代码质量
<output>
    建议估分: [在这里给出一个大概的分数，例如：85/100 左右]
    检查报告：供主助教参考的检查报告
</output>

<problem> 

</problem>
<code>
#include <stdio.h>

#define N 5

int main(void) {
    int nums[N];
    int i;

    printf("Enter %d numbers:\n", N);
    for (i = 0; i < N; i++) {
        if (scanf("%d", &nums[i]) != 1) {
            printf("Make sure that you input an int.\n");
            return 1;
        }
    }

    int min = nums[0];
    int max = nums[0];
    int sum = nums[0];
    for (i = 1; i < N; i++) {
        if (nums[i] < min){
            min = nums[i];
        }
        if (nums[i] > max){
            max = nums[i];
        }
        sum += nums[i];
    }
    float average = (float)sum / N;
    printf("Minimum: %d\n", min);
    printf("Maximum: %d\n", max);
    printf("Average: %f\n", average);

    return 0;
}
</code>
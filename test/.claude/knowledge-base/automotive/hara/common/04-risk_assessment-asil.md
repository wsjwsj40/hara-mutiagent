# HARA 风险评估 - ASIL 映射

## 使用方式

本文件是 ASIL 计算规则。大模型应先根据场景事实判断 S、E、C，再由工具或总控流程计算 `结果ASIL`。不要先设定 ASIL 再倒推 S/E/C。

## ASIL 等级映射

本项目的最终 ASIL 校验使用 S/E/C 后缀求和规则。

```text
score = S后缀 + E后缀 + C后缀
score <= 6 => QM
score == 7 => A
score == 8 => B
score == 9 => C
score >= 10 => D
```

示例：

```text
S3 + E4 + C3 = 10 => D
S3 + E3 + C3 = 9 => C
S2 + E4 + C2 = 8 => B
S1 + E2 + C3 = 6 => QM
```

如果模型初始填写的 `结果ASIL` 与该规则不一致，以 Python 工具校验后的结果为准，并在 `Validation_Warnings` 或阶段 `review_log` 中记录修正。

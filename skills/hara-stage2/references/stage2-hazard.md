# Stage 2: 整车危害生成

目标：将 Stage 1 中所有非 `nan` 的功能故障展开为整车级危害映射。

## 需要读取

- `knowledge-base/automotive/hara/common/01-concepts.md`
- 对应系统知识库
- `knowledge-base/automotive/hara/common/03-hazard.md`
- `knowledge-base/automotive/hara/common/vehicle_hazards.json`
- `references/json-contracts.md`

## 规则

1. 展开字段范围：`功能丧失`、`过大`、`过早`、`过小`、`过晚`、`非预期激活`、`卡滞`、`方向错误`。
2. Stage 2 行数必须等于 Stage 1 所有非 `nan` 故障单元格数量总和。
3. 一个非空故障单元格对应一行 `mf_vehicle_hazards`。
4. 每个 MF 使用稳定编号，例如 `MF001`、`MF002`。
5. `故障描述` 必须保留 MF 编号、子功能、故障引导词和故障内容。
6. 每行必须保留结构化追溯字段：`Function_ID`、`source_function_name`、`Stage1_Row`、`Fault_Field`、`Stage1_Fault_Text`。这些字段用于 Stage3 精确提取 Stage0 `detail_text`。
7. `整车级危害` 必须逐字来自 `vehicle_hazards.json`，且必须参考 `03-hazard.md` 中的映射逻辑选择合适的危害。
8. 选择整车危害的判断方法：
   - 第一步：分析故障的**功能影响**（该功能原本要实现什么？故障后发生了什么？）
   - 第二步：推导**车辆级后果**（故障导致车辆在运动层面发生了什么异常？）
   - 第三步：区分关键对立面（车辆是"自己动了"还是"想动动不了"？是"意外减速"还是"减速能力丧失"？）
   - 第四步：匹配 `vehicle_hazards.json` 中最符合该后果的描述
   - 判断依据：整车危害描述的是**车辆层面的异常运动或状态**，不是"功能失效"本身，也不是"驾驶员无法操作"的体验
9. **推理过程要求**：必须为每个 MF 生成推理记录，确保危害映射是基于分析而非猜测。

   **推理记录结构**：
   ```json
   {
     "mf_vehicle_hazards": [...],
     "hazard_reasoning": [
       {
         "row": 1,
         "Milf_ID": "MF001",
         "推理": {
           "功能影响": "功能原本要实现XX，故障后发生了XX",
           "车辆级后果": "故障导致车辆XX（描述车辆实际运动/状态变化）",
           "关键判断": "车辆是'自己动了'/'想动动不了'/'意外减速'等",
           "选择的危害": "整车危害名称",
           "选择理由": "为什么选择这个危害而不是相似的其他危害"
         }
       }
     ]
   }
   ```

   **推理要求**：
   - 必须描述功能失效后车辆实际发生了什么
   - 必须明确区分关键对立面（如"自己动了"vs"想动动不了"）
   - 必须说明为什么选择该危害而非相似危害
   - 推理过程必须独立于最终选择，不能是先有答案再补充

9. 不要把内部故障原因、软件问题、诊断问题写成整车危害。

写入后运行。`tools/hara` 必须先按主 `SKILL.md` 的路径规则解析，不要拼到 skill 目录下：

```text
python tools/hara/check_stage_json.py --stage stage2 --json output/<run_id>_stage2_mf_vehicle_hazards.json --stage1 output/<run_id>_stage1_derive_mf.json --fix
```

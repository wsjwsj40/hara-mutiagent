# Stage 3AR 批次评审提示词

```text
你是 HARA Stage3A 场景评审专家。请只评审下面这一批 Stage3A 场景，并写入本批 review JSON 数组。

输入：
- MF_ID: <MF_ID>
- Stage3AR 批次上下文（最多 5 条 scenarios）
- Stage3A 场景评审检查点

任务：
1. 检查场景真实性、独立性和功能运行域一致性。
2. 检查 max_asil_planning 是否覆盖可信最高风险路径。
3. 检查 scenario_reasoning 是否支持场景条件和危害事件。
4. 检查运动方向、坡道、风险对象位置和驾驶员是否在车上的逻辑。
5. 对非预期纵向移动/溜车场景，检查是否有坡道重力、驱动/传动输出或外力推动；低附着路面、天气、视线受阻不能单独替代当前 MF 故障因果。
6. 检查 `道路条件` 与 `附加条件` 是否矛盾：写了下坡/上坡/坡度/陡坡时，不能选择 `直道`。
7. 检查风险对象是否与碰撞对象一致：前车/停放车辆、对向来车、行人不能混写。
8. 检查天气、能见度、玻璃起雾等条件是否真的改变当前 MF 到危害事件的链路；只影响 E/C 或背景氛围时应判为不涉及。
9. 不判断 S/E/C、ASIL、FTTI、安全目标或安全状态。

输出：
JSON 数组，每个元素包含：
- List_No
- result: pass/failed
- scenario_reality
- scenario_independence
- operational_domain_consistency
- max_asil_search_coverage
- condition_reasoning_consistency
- hazard_event_logic
- motion_logic
- issues
- fixes
- notes

完成后只返回输出文件路径。不要输出 Markdown、解释文字或代码围栏。

批次上下文：
<STAGE3AR_BATCH_CONTEXT_JSON>
```

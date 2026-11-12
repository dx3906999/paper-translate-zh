> 领域表示例（计算机系统 / 安全方向）。`glossary-core.md` 是通用措辞部分，两者一起给译者。
> 换领域时**复制这份**改成 `glossary-<你的领域>.md`，保留格式、替换词条；不要在原文件上改。

# 术语表示例：硬件模糊测试 / 处理器验证 / 体系结构

> 译前先看一遍；遇到表里没有的，按「行业通行译法 + 首次出现附英文」处理，并在回复里报备新增术语。

## 模糊测试与验证

| English | 中文 | 备注 |
|---|---|---|
| fuzzing | 模糊测试 | |
| fuzzer | 模糊测试器（fuzzer） | 首次出现带英文 |
| hardware fuzzing | 硬件模糊测试 | |
| test / test case / test pattern | 测试用例 / 测试图形 | pattern 用「测试图形」 |
| stimulus / stimuli | 测试激励 | 单数「激励」 |
| seed | 种子 | |
| corpus | 语料库 | |
| corpus scheduling | 语料调度 | |
| mutation | 变异 | |
| coverage | 覆盖率 | 具体指覆盖点数量时写「覆盖点」 |
| coverpoint / coverage point | 覆盖点 | |
| coverage instrumentation | 覆盖率插桩 | |
| coverage convergence | 覆盖率收敛 | |
| coverage feedback | 覆盖率反馈 | |
| DUT (design under test) | 被测设计（DUT） | |
| REF / reference model | 参考模型（REF） | |
| golden model | 黄金模型 | |
| self-checking | 自检 | |
| checker | 检查器 | |
| monitor | 监视器 | |
| mismatch | 失配 | |
| assertion | 断言 | |
| bug | 缺陷 | 硬件验证语境不用「漏洞」 |
| vulnerability | 漏洞 | 安全语境 |
| corner case | 边界情形 | |
| crash | 崩溃 | |

## 体系结构 / RTL

| English | 中文 |
|---|---|
| instruction encoding | 指令编码 |
| operand | 操作数 |
| register file | 寄存器堆 |
| control-flow instruction | 控制流指令 |
| basic block | 基本块 |
| branch / jump range | 分支 / 跳转范围 |
| pipeline | 流水线 |
| CSR (control and status register) | 控制状态寄存器（CSR） |
| trap / exception | 陷阱 / 异常 |
| cycle-accurate | 周期精确 |
| snapshot | 快照 |
| trace | 执行迹 / 跟踪记录 |
| RTL | 寄存器传输级（RTL） |
| programmable logic (PL) | 可编程逻辑（PL） |
| processing system (PS) | 处理系统（PS） |
| host | 主机 |
| overlay / bitstream | 覆盖层 / 比特流 |
| out-of-order | 乱序 |
| single-issue | 单发射 |
| sign extension | 符号扩展 |
| alignment | 对齐 |

## 实验与性能

| English | 中文 |
|---|---|
| throughput | 吞吐率 |
| latency | 延迟 |
| area overhead | 面积开销 |
| speedup | 加速比 |
| overhead | 开销 |
| resource utilization | 资源占用 |
| geometric mean | 几何平均 |
| benchmark | 基准测试（程序） |
| workload | 工作负载 |
| iteration | 轮次 / 迭代 |
| evaluation | 实验评估 / 评估 |
| baseline | 基线 |
| ablation | 消融 |
| prototype | 原型 |
| design space | 设计空间 |
| state reachability | 状态可达性 |

## 通用学术措辞

| English | 中文 |
|---|---|
| In this paper, we present … | 本文提出 … |
| To the best of our knowledge | 据我们所知 |
| state-of-the-art | 当前最优 / 最先进 |
| Experimental results show that … | 实验结果表明 … |
| compared with / against | 与 … 相比 |
| up to | 最高 / 最多（按语境，别写「高达」堆砌） |
| a factor of N | N 倍 |
| as shown in Fig. N | 如图 N 所示 |
| we argue / we observe | 我们认为 / 我们观察到 |
| Moreover / Furthermore / In addition | 此外 / 进一步地 / 另外（不要全用「此外」） |
| However | 然而（一段内别重复三次以上） |
| Note that | 注意 / 值得注意 |

## 常被译坏的词

- **verification** 验证；**validation** 确认；**evaluation** 评估 —— 三者别混。
- **emulation** 模拟（emulation），**simulation** 仿真。
- **design** 在 "design under test" 里是「被测设计」；在 "hardware design" 里是「硬件设计」；"the design" 有时指「设计（RTL）」。
- **test** 别一律译「测试」：test case 用例、test pattern 图形、test generation 测试生成。
- **instrumentation** 插桩，不是「仪器化」。
- **leverage** 利用 / 借助，不写「杠杆化」。
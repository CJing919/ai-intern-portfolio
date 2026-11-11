# -*- coding: utf-8 -*-
"""Generate deterministic synthetic data for the portfolio demos.

All company names, prices, policies and metrics in this repository are synthetic.
They are designed to exercise the code paths, not to describe a real employer.
"""

from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


FAQ_SEED = [
    {
        "group": "rental_process",
        "category": "租赁流程",
        "q": "环保设备租赁的流程是什么？",
        "a": "标准流程为：需求确认→选型报价→现场勘查→合同与押金→排产发货→安装调试→验收起租→维保与退租。常规设备 3—5 个工作日可发货；定制或跨省项目以合同排期为准。",
        "tags": ["租赁", "流程", "发货"],
    },
    {
        "group": "deposit",
        "category": "押金",
        "q": "租赁设备需要交多少押金？",
        "a": "押金通常按设备原值的 10%—20% 收取，不同设备差异较大。押金在设备验收后退还：无损坏、无欠费、耗材结清后 7—10 个工作日原路退回。",
        "tags": ["押金", "退款", "验收"],
    },
    {
        "group": "freight",
        "category": "运费",
        "q": "设备租赁的运费怎么计算？",
        "a": "运费由基础出车费、里程费和特殊吊装费组成，默认按单程 30 公里测算。上海区域内基础出车费 500 元，超出部分按 8 元/公里计；跨省项目需单独报价。",
        "tags": ["运费", "物流", "跨省"],
    },
    {
        "group": "installation",
        "category": "安装调试",
        "q": "设备到场后由谁负责安装调试？",
        "a": "标准租赁包含一次进场安装与调试，通电、通水、基础条件由客户准备。调试完成后双方签署验收单，起租日以验收单日期为准；二次移位或改造另行收费。",
        "tags": ["安装", "调试", "验收"],
    },
    {
        "group": "maintenance",
        "category": "维保",
        "q": "租赁期间设备故障如何维保？",
        "a": "租赁期内提供 7×24 小时报修，上海区域 2 小时内响应、4 小时内到场；一般故障 8 小时内修复，重大故障提供备用机。人为损坏和耗材更换不在免费维保范围内。",
        "tags": ["维保", "故障", "响应"],
    },
    {
        "group": "invoice",
        "category": "发票",
        "q": "租赁费用可以开什么发票？",
        "a": "可开具 13% 增值税专用发票或普通发票，服务类项目按 6% 开具。发票在首期款到账后 3 个工作日内开出，专票需提前提供开票资料和邮寄地址。",
        "tags": ["发票", "税率", "专票"],
    },
    {
        "group": "contract",
        "category": "合同",
        "q": "签合同需要准备哪些资料？",
        "a": "企业客户需提供营业执照、开票资料、经办人授权书和项目地址；个人客户需提供身份证与使用场景说明。合同可走电子签，特殊条款需提前走法务审批。",
        "tags": ["合同", "资料", "电子签"],
    },
    {
        "group": "lease_term",
        "category": "租期",
        "q": "设备最短可以租多久？",
        "a": "标准设备最短租期 7 天，监测类设备最短 30 天。租期不足最短天数按最短天数计费；连续租赁 30 天以上可申请 12% 的阶梯折扣。",
        "tags": ["租期", "最短", "折扣"],
    },
    {
        "group": "renewal",
        "category": "续租",
        "q": "租期到了还想继续用，怎么续租？",
        "a": "到期前 7 天提交续租申请，确认设备状态和下一周期价格后签署补充协议即可。连续续租通常保留原设备，若原设备已排给其他项目，可协调同型号替换。",
        "tags": ["续租", "补充协议", "替换"],
    },
    {
        "group": "return",
        "category": "退租",
        "q": "退租需要提前多久申请？",
        "a": "标准退租需提前 7 个工作日提交申请，便于安排拆除、运输和验收。提前退租按合同约定收取剩余租期 20% 的违约金；因设备质量问题退租可协商减免。",
        "tags": ["退租", "申请", "违约金"],
    },
    {
        "group": "quote",
        "category": "报价",
        "q": "设备租赁报价包含哪些费用？",
        "a": "报价通常包含设备租金、基础安装调试、常规维保和一次进出场运输。押金、特殊吊装、超距离运费、耗材和二次移位需单列，最终以报价单和合同为准。",
        "tags": ["报价", "费用", "押金"],
    },
    {
        "group": "delivery",
        "category": "发货",
        "q": "下单后多久可以发货？",
        "a": "现货设备在合同、首期款和押金到账后 3—5 个工作日发货；需要校准或改装的监测设备增加 2—3 个工作日。紧急项目可申请加急，是否可插单以库存确认为准。",
        "tags": ["发货", "现货", "加急"],
    },
    {
        "group": "fault",
        "category": "故障",
        "q": "设备出现故障怎么报修？",
        "a": "可通过服务热线、企业微信或合同预留邮箱报修，需提供设备编号、故障现象、现场照片和联系人。系统会生成工单并按区域派单，紧急故障可标记为 P1。",
        "tags": ["故障", "报修", "工单"],
    },
    {
        "group": "data_access",
        "category": "数据接入",
        "q": "监测数据可以接入我们的平台吗？",
        "a": "支持 Modbus RTU/TCP、MQTT、HTTP 推送和 4G DTU 等方式接入。标准项目提供点位表、协议文档和联调支持；定制协议对接按工作量单独评估。",
        "tags": ["数据", "接口", "MQTT"],
    },
    {
        "group": "calibration",
        "category": "校准",
        "q": "监测设备多久校准一次？",
        "a": "扬尘和噪声设备建议每 6 个月校准一次，水质设备按参数每 1—3 个月校准。租赁期内可购买校准包，含标准气体/标准液、现场校准和报告。",
        "tags": ["校准", "监测", "报告"],
    },
    {
        "group": "acceptance",
        "category": "环保验收",
        "q": "租赁设备能用于环保验收吗？",
        "a": "可以用于验收期间的临时监测或治理，但验收是否通过取决于项目工艺、排放条件和当地要求。我们可提供设备检定证书、运行记录和监测报告模板，不承诺验收结果。",
        "tags": ["验收", "环保", "证书"],
    },
    {
        "group": "subsidy",
        "category": "政策补贴",
        "q": "设备租赁可以申请环保补贴吗？",
        "a": "部分地区的绿色技改、污染防治或中小企业设备更新政策可能覆盖租赁费用，具体以当地申报指南为准。我们可协助提供合同、发票、设备清单和运行数据等材料。",
        "tags": ["补贴", "政策", "材料"],
    },
    {
        "group": "payment",
        "category": "付款",
        "q": "租赁费用怎么支付？",
        "a": "标准付款方式为 3:6:1，即合同签订付 30%、设备验收付 60%、退租结算付 10%。长期项目可按月支付，需通过信用评估；押金单独收取，不计入租金。",
        "tags": ["付款", "分期", "押金"],
    },
    {
        "group": "tax",
        "category": "税率",
        "q": "设备租赁的税率是多少？",
        "a": "有形动产租赁按 13% 增值税税率开具，纯技术服务按 6% 开具。合同会拆分设备租金、运输、安装和技术服务，具体税率以税务认定和合同约定为准。",
        "tags": ["税率", "增值税", "合同"],
    },
    {
        "group": "model",
        "category": "型号",
        "q": "怎么选择适合的设备型号？",
        "a": "需要确认处理对象、风量/水量、浓度、场地尺度和排放标准，再由工程师做选型。仅提供“房间面积”无法准确选型，建议提供工艺流程图或现场照片。",
        "tags": ["选型", "型号", "工况"],
    },
    {
        "group": "capacity",
        "category": "处理量",
        "q": "设备的处理量怎么核算？",
        "a": "水处理按吨/天或吨/小时核算，废气按风量 m³/h 核算，除尘按过滤面积和入口浓度核算。选型时通常预留 10%—20% 余量，避免满负荷连续运行。",
        "tags": ["处理量", "选型", "余量"],
    },
    {
        "group": "power",
        "category": "电源",
        "q": "设备对现场电源有什么要求？",
        "a": "常规一体化设备为 380V 三相五线，监测类设备可用 220V 市电或太阳能供电。现场需提供独立空开、可靠接地和防雨配电箱，功率以设备铭牌为准。",
        "tags": ["电源", "380V", "现场"],
    },
    {
        "group": "site",
        "category": "场地",
        "q": "设备安装需要多大场地？",
        "a": "需要根据设备外形、检修通道和吊装空间确定，通常四周预留 1—1.5 米检修通道。楼顶、地下室或软基场地需额外做承重和排水评估。",
        "tags": ["场地", "承重", "安装"],
    },
    {
        "group": "training",
        "category": "培训",
        "q": "租赁后会对我们的人员做培训吗？",
        "a": "标准租赁包含 1 次 2 小时现场培训，覆盖开关机、日常巡检、耗材更换和简单故障处理。可追加线上复训或录制操作视频，培训签到和考核记录可存档。",
        "tags": ["培训", "操作", "巡检"],
    },
    {
        "group": "insurance",
        "category": "保险",
        "q": "设备损坏或丢失有保险吗？",
        "a": "标准租金不含设备财产险，客户对租赁期内的设备安全负责。可代购设备财产险和第三方责任险，保费按设备原值的 0.3%—0.8% 评估。",
        "tags": ["保险", "损坏", "责任"],
    },
    {
        "group": "penalty",
        "category": "违约金",
        "q": "提前退租或逾期归还有什么违约金？",
        "a": "提前退租按剩余租期租金的 20% 收取违约金；逾期归还按日租金的 1.5 倍计收，超过 7 天可视为设备丢失并启动赔付。不可抗力可凭证明协商。",
        "tags": ["违约金", "逾期", "退租"],
    },
    {
        "group": "backup",
        "category": "备用机",
        "q": "设备维修期间有备用机吗？",
        "a": "连续租赁 30 天以上或合同约定 SLA 的项目，重大故障 24 小时内提供同型号备用机。备用机需签交接单，故障机修复后归还，备用期按正常租金计。",
        "tags": ["备用机", "SLA", "维修"],
    },
    {
        "group": "consumables",
        "category": "耗材",
        "q": "租赁期间的耗材由谁承担？",
        "a": "滤芯、药剂、标准气体、传感器膜片等耗材默认由客户承担，可购买耗材包由我们统一配送。耗材价格在合同附件中列明，紧急采购需另计加急费。",
        "tags": ["耗材", "滤芯", "药剂"],
    },
    {
        "group": "platform",
        "category": "软件平台",
        "q": "设备数据可以在手机上查看吗？",
        "a": "标配 Web 管理后台，支持手机浏览器查看实时数据、历史曲线和报警。需要微信小程序、企业微信推送或私有化部署的，按项目单独报价。",
        "tags": ["平台", "手机", "报警"],
    },
    {
        "group": "data_ownership",
        "category": "数据归属",
        "q": "设备采集的数据归谁所有？",
        "a": "原始监测数据归客户所有，我们仅为运维和报表目的在授权范围内使用。项目结束后可按约定导出或删除数据，涉及个人信息的数据需单独签署处理协议。",
        "tags": ["数据", "归属", "隐私"],
    },
]


def _variants(seed: dict) -> list[str]:
    q = seed["q"].rstrip("？?")
    category = seed["category"]
    return [
        seed["q"],
        f"请问{q}？",
        f"我想了解一下，{q}？",
        f"想问下{q}？",
        q,
        f"关于{category}，{q}？",
        f"签合同前想确认一下：{q}？",
    ]


def generate_faq() -> tuple[list[dict], list[dict]]:
    docs: list[dict] = []
    for seed in FAQ_SEED:
        for i, question in enumerate(_variants(seed), start=1):
            docs.append(
                {
                    "id": f"faq-{seed['group']}-{i:02d}",
                    "group_id": seed["group"],
                    "category": seed["category"],
                    "question": question,
                    "answer": seed["a"],
                    "tags": seed["tags"],
                    "source": "synthetic-faq-v1",
                    "synthetic": True,
                }
            )

    # 40 FAQ eval queries: two different paraphrases for each of the first 20 groups.
    eval_rows: list[dict] = []
    for seed in FAQ_SEED[:20]:
        variants = _variants(seed)
        picks = [variants[1], variants[3]]
        for j, q in enumerate(picks, start=1):
            eval_rows.append(
                {
                    "id": f"eval-faq-{seed['group']}-{j}",
                    "question": q,
                    "expected_groups": [seed["group"]],
                    "expected_intent": "faq",
                    "expected_tool": "search_knowledge_base",
                    "difficulty": "easy",
                }
            )

    # 10 hard paraphrases: deliberately avoid the exact FAQ vocabulary.
    hard_faq = [
        ("return", "设备用完了想提前还回去，要提前几天说？"),
        ("deposit", "押金一般压多少，什么时候能退回来？"),
        ("tax", "开票要几个点？"),
        ("maintenance", "机器坏了，师傅多久能到？"),
        ("site", "设备放在楼顶，承重要不要另外算？"),
        ("data_access", "我们想接政府平台，能对接吗？"),
        ("acceptance", "项目验收需要哪些证书？"),
        ("training", "人可以来现场教我们操作吗？"),
        ("insurance", "设备被偷了怎么办？"),
        ("penalty", "晚还几天怎么算钱？"),
    ]
    for i, (group, q) in enumerate(hard_faq, start=1):
        eval_rows.append(
            {
                "id": f"eval-hard-{i:02d}",
                "question": q,
                "expected_groups": [group],
                "expected_intent": "faq",
                "expected_tool": "search_knowledge_base",
                "difficulty": "hard",
            }
        )


    tool_rows = [
        ("租赁 2 台移动式污水处理设备 10 天，大概多少钱？", "quote", "get_quote"),
        ("扬尘监测设备租一个月，3 台，含安装，报价多少？", "quote", "get_quote"),
        ("工业除尘设备租 5 天 1 台，运费按 20 公里算，总费用是多少？", "quote", "get_quote"),
        ("2 台噪声监测仪租 15 天报价", "quote", "get_quote"),
        ("订单 EQ2026003 现在什么进度？", "order", "get_order_status"),
        ("帮我查一下 EQ2026007 什么时候到货", "order", "get_order_status"),
        ("EQ2026001 的押金退了吗？", "order", "get_order_status"),
        ("设备故障三天没人处理，我要投诉，转人工", "handoff", "create_handoff_ticket"),
        ("我要退款，请人工客服联系我", "handoff", "create_handoff_ticket"),
        ("租赁合同有纠纷，帮我转人工", "handoff", "create_handoff_ticket"),
    ]
    for i, (q, intent, tool) in enumerate(tool_rows, start=1):
        eval_rows.append(
            {
                "id": f"eval-tool-{i:02d}",
                "question": q,
                "expected_groups": [],
                "expected_intent": intent,
                "expected_tool": tool,
            }
        )
    return docs, eval_rows


ORDERS = [
    {
        "order_id": "EQ2026001",
        "customer": "上海某园区运营方",
        "equipment": "移动式污水处理设备",
        "quantity": 2,
        "status": "已退租",
        "current_step": "押金结算中",
        "eta": "押金预计 2026-11-15 前退回",
        "owner": "租赁服务组",
        "note": "设备已验收，无损坏，等待财务结算。",
    },
    {
        "order_id": "EQ2026002",
        "customer": "苏州某制造企业",
        "equipment": "工业除尘设备",
        "quantity": 1,
        "status": "履约中",
        "current_step": "安装调试",
        "eta": "2026-11-13 完成调试",
        "owner": "华东交付组",
        "note": "现场电源已就绪，等待风管接口改造。",
    },
    {
        "order_id": "EQ2026003",
        "customer": "浦东某工地",
        "equipment": "扬尘监测设备",
        "quantity": 4,
        "status": "履约中",
        "current_step": "物流运输",
        "eta": "2026-11-12 到货",
        "owner": "上海配送组",
        "note": "车牌沪A****，司机已联系现场收货人。",
    },
    {
        "order_id": "EQ2026004",
        "customer": "嘉兴某印染厂",
        "equipment": "废气处理设备",
        "quantity": 1,
        "status": "待发货",
        "current_step": "排产",
        "eta": "2026-11-18 发货",
        "owner": "生产计划组",
        "note": "催化燃烧模块需完成出厂检测。",
    },
    {
        "order_id": "EQ2026005",
        "customer": "上海某街道",
        "equipment": "噪声监测仪",
        "quantity": 6,
        "status": "履约中",
        "current_step": "数据联调",
        "eta": "2026-11-14 完成平台接入",
        "owner": "技术支持组",
        "note": "MQTT 主题已配置，等待客户平台白名单。",
    },
    {
        "order_id": "EQ2026006",
        "customer": "宁波某水务公司",
        "equipment": "水质在线监测仪",
        "quantity": 3,
        "status": "待付款",
        "current_step": "合同审批",
        "eta": "付款后 5 个工作日发货",
        "owner": "商务支持组",
        "note": "客户正在走内部用印流程。",
    },
    {
        "order_id": "EQ2026007",
        "customer": "昆山某电子厂",
        "equipment": "危废暂存柜",
        "quantity": 2,
        "status": "履约中",
        "current_step": "派送中",
        "eta": "2026-11-12 下午送达",
        "owner": "上海配送组",
        "note": "需客户准备叉车卸货。",
    },
    {
        "order_id": "EQ2026008",
        "customer": "上海某环保工程公司",
        "equipment": "环保管家服务",
        "quantity": 1,
        "status": "履约中",
        "current_step": "月度巡检",
        "eta": "2026-11-20 出具月报",
        "owner": "环保管家组",
        "note": "本月已完成 3 个点位巡检。",
    },
]


PRICING = {
    "equipment": [
        {"name": "移动式污水处理设备", "aliases": ["污水处理", "污水设备", "一体化污水"], "daily_rate": 880, "deposit": 8000, "setup_fee": 1500},
        {"name": "扬尘监测设备", "aliases": ["扬尘", "扬尘监测"], "daily_rate": 260, "deposit": 2000, "setup_fee": 600},
        {"name": "噪声监测仪", "aliases": ["噪声", "噪音"], "daily_rate": 180, "deposit": 1000, "setup_fee": 300},
        {"name": "工业除尘设备", "aliases": ["除尘", "工业除尘"], "daily_rate": 1200, "deposit": 15000, "setup_fee": 2500},
        {"name": "废气处理设备", "aliases": ["废气", "VOCs", "催化燃烧"], "daily_rate": 1500, "deposit": 20000, "setup_fee": 3000},
        {"name": "水质在线监测仪", "aliases": ["水质", "水质监测"], "daily_rate": 420, "deposit": 5000, "setup_fee": 1000},
        {"name": "危废暂存柜", "aliases": ["危废", "暂存柜"], "daily_rate": 320, "deposit": 3000, "setup_fee": 800},
        {"name": "环保管家服务", "aliases": ["环保管家", "管家服务"], "daily_rate": 6000, "deposit": 0, "setup_fee": 0},
    ],
    "delivery_base_fee": 500,
    "delivery_per_km": 8,
    "free_distance_km": 30,
    "tax_rate": 0.13,
    "long_rental_discounts": [
        {"min_days": 30, "discount": 0.12},
        {"min_days": 7, "discount": 0.05},
    ],
}


TOOL_SCHEMAS = [
    {
        "name": "search_knowledge_base",
        "description": "检索环保设备租赁 FAQ 知识库，返回带引用的答案片段。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "用户问题"},
                "top_k": {"type": "integer", "default": 3},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_quote",
        "description": "根据设备类型、数量、租期和运输距离计算租赁报价。",
        "parameters": {
            "type": "object",
            "properties": {
                "equipment_type": {"type": "string"},
                "quantity": {"type": "integer"},
                "days": {"type": "integer"},
                "distance_km": {"type": "number", "default": 30},
            },
            "required": ["equipment_type", "quantity", "days"],
        },
    },
    {
        "name": "get_order_status",
        "description": "查询租赁订单的当前节点、预计时间和负责人。",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "create_handoff_ticket",
        "description": "创建人工接管工单，用于投诉、退款、合同纠纷等高风险场景。",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "summary": {"type": "string"},
                "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
            },
            "required": ["reason", "summary"],
        },
    },
]


def generate_content() -> None:
    rng = random.Random(42)
    topics = [
        "环保设备租赁如何选型",
        "污水设备租赁的 5 个成本坑",
        "扬尘监测点位怎么布",
        "噪声监测设备租赁指南",
        "工业除尘改造的 3 个关键指标",
        "废气处理设备选型清单",
        "环保验收前要准备哪些材料",
        "设备租赁合同里的隐藏费用",
        "移动式污水设备现场安装要点",
        "水质在线监测的校准周期",
        "危废暂存柜怎么选",
        "环保管家服务包含什么",
        "设备租赁押金怎么退",
        "跨省运输的注意事项",
        "设备故障应急处理流程",
        "监测数据接入政府平台",
        "中小企业环保技改补贴",
        "租赁发票和税率怎么算",
        "备用机条款怎么谈",
        "耗材成本怎么控制",
        "设备退租验收标准",
        "环保设备租赁的付款方式",
        "如何评估设备供应商",
        "冬季设备防冻清单",
        "园区污水站托管运营",
        "扬尘监测数据异常排查",
        "活性炭更换周期怎么定",
        "环保设备保险要不要买",
        "设备租赁的 SLA 怎么写",
        "环保项目投标文件怎么拆",
    ]
    channels = ["公众号", "小红书", "视频号"]
    content_types = ["图文", "短视频", "案例"]
    audiences = ["环保工程公司", "制造企业 EHS", "园区运营方", "工地项目经理"]

    calendar_rows = []
    start = date(2026, 8, 1)
    for i in range(30):
        d = start + timedelta(days=i)
        calendar_rows.append(
            {
                "date": d.isoformat(),
                "channel": channels[i % 3],
                "content_type": content_types[i % 3],
                "topic": topics[i],
                "audience": audiences[i % len(audiences)],
                "keyword": ["环保设备租赁", "污水处理", "扬尘监测", "废气治理", "环保验收"][i % 5],
                "status": "已发布" if i < 24 else "待审核",
            }
        )
    with (DATA / "content" / "calendar.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(calendar_rows[0].keys()))
        writer.writeheader()
        writer.writerows(calendar_rows)

    performance_rows = []
    channel_params = {
        "公众号": {"views": (800, 2600), "eng": (0.025, 0.055), "lead": (0.004, 0.012), "spend": (300, 800)},
        "小红书": {"views": (1500, 6200), "eng": (0.045, 0.09), "lead": (0.006, 0.018), "spend": (200, 600)},
        "视频号": {"views": (2000, 8200), "eng": (0.035, 0.08), "lead": (0.008, 0.022), "spend": (250, 700)},
    }
    for i in range(30):
        d = start + timedelta(days=i)
        for j, channel in enumerate(channels):
            p = channel_params[channel]
            trend = 1 + (i / 30) * 0.18
            views = int(rng.uniform(*p["views"]) * trend)
            eng = rng.uniform(*p["eng"])
            likes = int(views * eng * 0.7)
            comments = int(views * eng * 0.2)
            shares = int(views * eng * 0.1)
            leads = max(2, int(views * rng.uniform(*p["lead"])))
            spend = round(rng.uniform(*p["spend"]), 2)
            performance_rows.append(
                {
                    "date": d.isoformat(),
                    "channel": channel,
                    "content_type": content_types[(i + j) % 3],
                    "topic": topics[(i + j) % len(topics)],
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "leads": leads,
                    "spend": spend,
                }
            )
    with (DATA / "content" / "performance.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(performance_rows[0].keys()))
        writer.writeheader()
        writer.writerows(performance_rows)


def generate_process() -> None:
    rows = [
        ("运营流程", "O01", "客户需求登记", "运营", 12, 420, 0.85, 2, 0.9, "微信群+Excel 手工登记"),
        ("运营流程", "O02", "设备选型", "技术", 45, 180, 0.55, 3, 0.7, "依赖工程师经验"),
        ("运营流程", "O03", "报价审批", "商务", 60, 150, 0.8, 2, 0.8, "多版本 Excel 易出错"),
        ("运营流程", "O04", "合同用印", "法务", 35, 120, 0.6, 4, 0.5, "线下流转"),
        ("运营流程", "O05", "排产调度", "交付", 50, 110, 0.5, 4, 0.6, "库存与排期不同步"),
        ("运营流程", "O06", "发货跟踪", "交付", 20, 300, 0.75, 2, 0.85, "物流信息分散"),
        ("运营流程", "O07", "退租结算", "财务", 40, 90, 0.7, 3, 0.75, "押金与耗材对账慢"),
        ("客服流程", "C01", "日常咨询响应", "客服", 8, 900, 0.9, 1, 0.9, "重复问题多"),
        ("客服流程", "C02", "故障派单", "客服", 15, 260, 0.65, 3, 0.6, "工单靠人工分派"),
        ("客服流程", "C03", "投诉处理", "客服主管", 55, 45, 0.25, 5, 0.4, "高情绪、高风险"),
        ("客服流程", "C04", "客户回访", "客服", 12, 180, 0.7, 2, 0.7, "回访记录不完整"),
        ("新媒体流程", "M01", "选题", "运营", 30, 60, 0.8, 1, 0.8, "依赖个人灵感"),
        ("新媒体流程", "M02", "脚本撰写", "运营", 60, 60, 0.75, 2, 0.6, "重复结构多"),
        ("新媒体流程", "M03", "配图/剪辑", "设计", 90, 60, 0.6, 1, 0.5, "外包沟通成本高"),
        ("新媒体流程", "M04", "内容审核", "市场负责人", 20, 60, 0.4, 3, 0.5, "合规风险"),
        ("新媒体流程", "M05", "发布与数据回收", "运营", 25, 60, 0.85, 1, 0.9, "多平台手工复制"),
        ("数据流程", "D01", "日报取数", "运营", 45, 220, 0.9, 1, 0.95, "SQL 重复编写"),
        ("数据流程", "D02", "周报分析", "运营", 120, 30, 0.6, 2, 0.7, "口径不一致"),
        ("数据流程", "D03", "客户标签更新", "运营", 30, 150, 0.7, 2, 0.6, "标签规则散落"),
    ]
    with (DATA / "environment" / "process_steps.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["flow", "step_id", "step", "owner", "avg_minutes", "monthly_volume", "automation_potential", "risk", "data_ready", "notes"]
        )
        writer.writerows(rows)


def main() -> None:
    for directory in [
        DATA / "customer_service",
        DATA / "content",
        DATA / "environment" / "bid_docs",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    docs, eval_rows = generate_faq()
    with (DATA / "customer_service" / "faq.jsonl").open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    with (DATA / "customer_service" / "eval_set.jsonl").open("w", encoding="utf-8") as f:
        for row in eval_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (DATA / "customer_service" / "orders.json").open("w", encoding="utf-8") as f:
        json.dump(ORDERS, f, ensure_ascii=False, indent=2)
    with (DATA / "customer_service" / "pricing.json").open("w", encoding="utf-8") as f:
        json.dump(PRICING, f, ensure_ascii=False, indent=2)
    with (DATA / "customer_service" / "tool_schemas.json").open("w", encoding="utf-8") as f:
        json.dump(TOOL_SCHEMAS, f, ensure_ascii=False, indent=2)

    generate_content()
    generate_process()
    print(f"FAQ docs: {len(docs)}")
    print(f"Eval rows: {len(eval_rows)}")
    print("Synthetic data generated in data/")


if __name__ == "__main__":
    main()

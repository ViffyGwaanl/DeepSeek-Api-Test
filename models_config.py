# models_config.py

MODELS_CONFIG = {
    "deepseek-r1-bd": {
        "display_name": "百度DeepSeek-R1",
        "url": "https://qianfan.baidubce.com/v2/chat/completions", 
        "api_key": "bxx3/Axxk/xx4",
        "payload_model": "deepseek-r1"
    },
    "deepseek-r1-ali": {
        "display_name": "阿里DeepSeek-R1",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "api_key": "sk-xx",
        "payload_model": "deepseek-r1"
    },
    "deepseek-r1-sil": {
        "display_name": "硅基流动DeepSeek-R1",
        "url": "https://api.siliconflow.cn/v1/chat/completions",
        "api_key": "sk-xx",
        "payload_model": "Pro/deepseek-ai/DeepSeek-R1"
    },
    "deepseek-r1-bytedance": {
        "display_name": "字节DeepSeek-R1",
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "api_key": "xx",
        "payload_model": "ep-xx"
    },
    "deepseek-reasoner": {
        "display_name": "官网DeepSeek-R1",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "api_key": "sk-xx",
        "payload_model": "deepseek-reasoner"
    },
        "deepseek-r1-luc": {
        "display_name": "潞晨云DeepSeek-R1",
        "url": "https://cloud.luchentech.com/api/maas/chat/completions",
        "api_key": "xx",
        "payload_model": "VIP/deepseek-ai/DeepSeek-R1"
    },
        "deepseek-r1-sens": {
        "display_name": "商汤DeepSeek-R1",
        "url": "https://api.sensenova.cn/compatible-mode/v1/chat/completions",
        "api_key": "sk-xx",
        "payload_model": "DeepSeek-R1"
    },
        "deepseek-r1-infini": {
        "display_name": "无问苍穹DeepSeek-R1",
        "url": "https://cloud.infini-ai.com/maas/v1/chat/completions",
        "api_key": "sk-xx",
        "payload_model": "deepseek-r1"
    },
        "deepseek-r1-ppinfra": {
        "display_name": "欧派云DeepSeek-R1",
        "url": "https://api.ppinfra.com/v3/openai/chat/completions",
        "api_key": "sk_xx",
        "payload_model": "deepseek/deepseek-r1"
    },
}

MODELS_TO_TEST = [
    "deepseek-r1-bd",
    "deepseek-r1-ali",
    "deepseek-r1-sil",
    "deepseek-r1-bytedance",
    "deepseek-reasoner",
    "deepseek-r1-luc",
    "deepseek-r1-sens",
    "deepseek-r1-infini",
    "deepseek-r1-ppinfra"
]

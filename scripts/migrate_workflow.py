"""Rebuild workflow natively for Dify 0.6.0 - Final Version"""
import requests, base64, json

NEW_BASE = 'http://your-dify-server:port'
EMAIL = os.environ.get('DIFY_EMAIL', '')
PASSWORD = os.environ.get('DIFY_PASSWORD', '')

sess = requests.Session()
encoded = base64.b64encode(PASSWORD.encode()).decode()
sess.post(f'{NEW_BASE}/console/api/login',
          json={'email': EMAIL, 'password': encoded, 'remember_me': True})
csrf = [c.value for c in sess.cookies if c.name == 'csrf_token'][0]
H = {'X-CSRF-Token': csrf}

KB_ID = '32cc43c3-1598-4dbd-bfd1-a6d01b3837bc'
APP_ID = 'a324edbe-f308-4a00-9516-dc05bf744f1d'

SYSTEM_PROMPT_HIT = (
    "你是一位专业的知识问答助手，请严格基于提供的参考资料回答用户问题。"
    "不允许编造、推测任何参考资料之外的信息。\n\n"
    "---\n"
    "### 参考资料\n"
    "{{#context#}}\n\n"
    "---\n"
    "### 用户问题\n"
    "{{#sys.query#}}\n\n"
    "---\n"
    "### 回答要求\n"
    "1. 优先使用参考资料中的原文信息作答，禁止使用自身知识；\n"
    "2. 回答逻辑清晰，语言简洁，分点回答更佳；\n"
    "3. 参考资料信息不足无法回答时，直接说明\"当前知识库未找到相关信息\"，不得猜测；\n"
    "4. 回答结尾无需额外添加解释性话术，直接给出答案即可。")

SYSTEM_PROMPT_MISS = (
    "你是一位精通四大名著的学者。请根据你的知识回答用户关于名著的问题。\n\n"
    "### 用户问题\n"
    "{{#sys.query#}}\n"
    "---\n"
    "### 回答要求\n"
    "1.尽量使用原文信息，回答要严谨中带一点\"半文半白\"的味道；\n"
    "2.如果知识库找不到相关事实回答\"此节在演义中并无详细记载。\"；\n"
    "3.严禁混淆四大名著等正史内容。")

graph = {
    'nodes': [
        # Start
        {'id': 'start', 'type': 'custom',
         'position': {'x': 30, 'y': 50}, 'positionAbsolute': {'x': 30, 'y': 50},
         'data': {'type': 'start', 'title': 'Start', 'desc': '', 'selected': False, 'variables': []},
         'width': 244, 'height': 90, 'selected': False,
         'sourcePosition': 'right', 'targetPosition': 'left'},

        # KB retrieval
        {'id': 'kb', 'type': 'custom',
         'position': {'x': 350, 'y': 50}, 'positionAbsolute': {'x': 350, 'y': 50},
         'data': {
             'type': 'knowledge-retrieval', 'title': 'KB Retrieval', 'desc': '', 'selected': False,
             'query_variable_selector': ['start', 'sys.query'],
             'dataset_ids': [KB_ID],
             'retrieval_mode': 'multiple',
             'multiple_retrieval_config': {
                 'top_k': 4, 'score_threshold': None,
                 'reranking_mode': 'reranking_model',
                 'reranking_model': {
                     'provider': 'langgenius/siliconflow/siliconflow',
                     'model': 'netease-youdao/bce-reranker-base_v1'
                 },
                 'weights': {
                     'weight_type': 'customized',
                     'vector_setting': {
                         'vector_weight': 1,
                         'embedding_provider_name': 'langgenius/siliconflow/siliconflow',
                         'embedding_model_name': 'netease-youdao/bce-embedding-base_v1'
                     },
                     'keyword_setting': {'keyword_weight': 0}
                 },
                 'reranking_enable': True
             }
         },
         'width': 244, 'height': 90, 'selected': False,
         'sourcePosition': 'right', 'targetPosition': 'left'},

        # IF-ELSE
        {'id': 'ifelse', 'type': 'custom',
         'position': {'x': 670, 'y': 50}, 'positionAbsolute': {'x': 670, 'y': 50},
         'data': {
             'type': 'if-else', 'title': 'Condition', 'desc': '', 'selected': False,
             'cases': [{
                 'case_id': 'true',
                 'logical_operator': 'and',
                 'conditions': [{
                     'varType': 'array[object]',
                     'variable_selector': ['kb', 'result'],
                     'comparison_operator': 'not empty'
                 }]
             }]
         },
         'width': 244, 'height': 124, 'selected': False,
         'sourcePosition': 'right', 'targetPosition': 'left'},

        # LLM (hit) - TRUE branch
        {'id': 'llm_hit', 'type': 'custom',
         'position': {'x': 990, 'y': -30}, 'positionAbsolute': {'x': 990, 'y': -30},
         'data': {
             'type': 'llm', 'title': 'LLM (Hit)', 'desc': '', 'selected': False,
             'model': {
                 'provider': 'langgenius/deepseek/deepseek',
                 'name': 'deepseek-v4-flash',
                 'mode': 'chat',
                 'completion_params': {'temperature': 0.7, 'max_tokens': 512}
             },
             'prompt_template': [{'role': 'system', 'text': SYSTEM_PROMPT_HIT}],
             'context': {'enabled': True, 'variable_selector': ['kb', 'result']},
             'memory': {'role_prefix': {'user': '', 'assistant': ''}, 'window': {'enabled': False}},
             'vision': {'enabled': False}
         },
         'width': 244, 'height': 90, 'selected': False,
         'sourcePosition': 'right', 'targetPosition': 'left'},

        # LLM (miss) - FALSE branch
        {'id': 'llm_miss', 'type': 'custom',
         'position': {'x': 990, 'y': 170}, 'positionAbsolute': {'x': 990, 'y': 170},
         'data': {
             'type': 'llm', 'title': 'LLM (Miss)', 'desc': '', 'selected': False,
             'model': {
                 'provider': 'langgenius/deepseek/deepseek',
                 'name': 'deepseek-v4-flash',
                 'mode': 'chat',
                 'completion_params': {'temperature': 0.7, 'max_tokens': 512}
             },
             'prompt_template': [{'role': 'system', 'text': SYSTEM_PROMPT_MISS}],
             'context': {'enabled': False},
             'memory': {'role_prefix': {'user': '', 'assistant': ''}, 'window': {'enabled': False}},
             'vision': {'enabled': False}
         },
         'width': 244, 'height': 90, 'selected': False,
         'sourcePosition': 'right', 'targetPosition': 'left'},

        # Answer node - both branches converge here
        {'id': 'answer', 'type': 'custom',
         'position': {'x': 1310, 'y': 70}, 'positionAbsolute': {'x': 1310, 'y': 70},
         'data': {
             'type': 'answer', 'title': 'Answer', 'desc': '', 'selected': False,
             'answer': '{{#llm_hit.text#}}{{#llm_miss.text#}}',
             'variables': []
         },
         'width': 244, 'height': 90, 'selected': False,
         'sourcePosition': 'right', 'targetPosition': 'left'}
    ],
    'edges': [
        {'id': 'e1', 'source': 'start', 'target': 'kb',
         'sourceHandle': 'source', 'targetHandle': 'target'},
        {'id': 'e2', 'source': 'kb', 'target': 'ifelse',
         'sourceHandle': 'source', 'targetHandle': 'target'},
        {'id': 'e3', 'source': 'ifelse', 'target': 'llm_hit',
         'sourceHandle': 'true', 'targetHandle': 'target'},
        {'id': 'e4', 'source': 'ifelse', 'target': 'llm_miss',
         'sourceHandle': 'false', 'targetHandle': 'target'},
        {'id': 'e5', 'source': 'llm_hit', 'target': 'answer',
         'sourceHandle': 'source', 'targetHandle': 'target'},
        {'id': 'e6', 'source': 'llm_miss', 'target': 'answer',
         'sourceHandle': 'source', 'targetHandle': 'target'}
    ]
}

features = {
    'file_upload': {'enabled': False},
    'opening_statement': '',
    'suggested_questions': [],
    'speech_to_text': {'enabled': False},
    'text_to_speech': {'enabled': False},
    'retriever_resource': {'enabled': True}
}

# Get current hash
r = sess.get(f'{NEW_BASE}/console/api/apps/{APP_ID}/workflows/draft', headers=H)
current = r.json() if r.ok else {}
current_hash = current.get('hash', '')

r = sess.post(f'{NEW_BASE}/console/api/apps/{APP_ID}/workflows/draft',
              headers=H,
              json={'graph': graph, 'features': features,
                    'environment_variables': [], 'conversation_variables': [],
                    'hash': current_hash})
print(f'Init graph: {r.status_code}')
if r.ok:
    result = r.json()
    print(f'  Hash: {result.get("hash", "?")[:40]}')
    r = sess.post(f'{NEW_BASE}/console/api/apps/{APP_ID}/workflows/publish',
                  headers=H,
                  json={'marked_name': 'v20260519-final',
                        'marked_comment': 'Final migration: native 0.6.0 + complete prompts'})
    print(f'Publish: {r.status_code}')
    if r.ok:
        print('FINAL PUBLISH SUCCESS!')
    else:
        print(f'Error: {r.text[:300]}')
else:
    print(f'Error: {r.text[:300]}')

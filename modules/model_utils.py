import copy
import torch
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cuda.matmul.allow_tf32 = True
from rwkv.model import RWKV
from rwkv.utils import PIPELINE

class ModelUtils:

  model = None
  pipline = None
  model_path = None
  strategy = None
  AVOID_REPEAT_TOKENS = []
  CHUNK_LEN = 256
  END_OF_TEXT = 0
  END_OF_LINE = 187
  CHAT_LEN_SHORT = 40
  CHAT_LEN_LONG = 150
  all_state = {}
  user = "Bob"
  bot = "Alice"
  
  def __init__(self, args):
    self.model_path = args.model
    self.strategy = args.strategy

  def load_model(self):
    self.model = RWKV(model=self.model_path, strategy=self.strategy)
    self.pipeline = PIPELINE(self.model, f"./20B_tokenizer.json")
    AVOID_REPEAT = '，：？！'
    for i in AVOID_REPEAT:
      dd = self.pipeline.encode(i)
      assert len(dd) == 1
      self.AVOID_REPEAT_TOKENS += dd

  def run_rnn(self, model_tokens, model_state, tokens, newline_adj = 0):
    tokens = [int(x) for x in tokens]
    model_tokens += tokens
    while len(tokens) > 0:
      out, model_state = self.model.forward(tokens[:self.CHUNK_LEN], model_state)
      tokens = tokens[self.CHUNK_LEN:]
    out[self.END_OF_LINE] += newline_adj # adjust \n probability
    if model_tokens[-1] in self.AVOID_REPEAT_TOKENS:
      out[model_tokens[-1]] = -999999999
    return out, model_tokens, model_state
  
  def save_all_stat(self, srv, name, last_out, model_tokens, model_state):
    n = f'{name}_{srv}'
    self.all_state[n] = {}
    self.all_state[n]['out'] = last_out
    self.all_state[n]['rnn'] = copy.deepcopy(model_state)
    self.all_state[n]['token'] = copy.deepcopy(model_tokens)

  def load_all_stat(self, srv, name):
    n = f'{name}_{srv}'
    model_state = copy.deepcopy(self.all_state[n]['rnn'])
    model_tokens = copy.deepcopy(self.all_state[n]['token'])
    return self.all_state[n]['out'], model_tokens, model_state
  
  def get_reply(self, model_tokens, model_state, out, x_temp, x_top_p, presence_penalty, frequency_penalty, user='', bot=''):
    if not user:
      user = self.user
    if not bot:
      bot = self.bot
    new_reply = ''
    begin = len(model_tokens)
    out_last = begin
    occurrence = {}
    for i in range(999):
      if i <= 0:
        newline_adj = -999999999
      elif i <= self.CHAT_LEN_SHORT:
        newline_adj = (i - self.CHAT_LEN_SHORT) / 10
      elif i <= self.CHAT_LEN_LONG:
        newline_adj = 0
      else:
        newline_adj = (i - self.CHAT_LEN_LONG) * 0.25 # MUST END THE GENERATION
      for n in occurrence:
        out[n] -= (presence_penalty + occurrence[n] * frequency_penalty)
      token = self.pipeline.sample_logits(out, temperature=x_temp, top_p=x_top_p)
      if token not in occurrence:
        occurrence[token] = 1
      else:
        occurrence[token] += 1
      
      out, model_tokens, model_state = self.run_rnn(model_tokens, model_state, [token], newline_adj=newline_adj)
      out[self.END_OF_TEXT] = -999999999  # disable <|endoftext|>

      xxx = self.pipeline.decode(model_tokens[out_last:])
      if '\ufffd' not in xxx: # avoid utf-8 display issues
        new_reply += xxx
        out_last = begin + i + 1
    
      send_msg = self.pipeline.decode(model_tokens[begin:])
      stop_text = (f'{user}：', f'{user}:', f'{bot}：', f'{bot}:')
      stop_flag = False
      for st in stop_text:
        if send_msg.endswith(st):
          send_msg = send_msg[:-len(st)].strip()
          stop_flag = True
          break
      if stop_flag:
        break
    return send_msg, out, model_tokens, model_state
  
  def get_default_prompt(self, background_adv = '', user='', bot=''):
    if not user:
      user = self.user
    if not bot:
      bot = self.bot
    init_prompt = f'''
    The following is a coherent verbose detailed conversation between a Chinese girl named {bot} and her friend {user}. \
    {bot} is very intelligent, creative and friendly. \
    {bot} likes to tell {user} a lot about herself and her opinions. \
    {bot} usually gives {user} kind, helpful and informative advices.
    {user}: lhc
    {bot}: LHC是指大型强子对撞机（Large Hadron Collider），是世界最大最强的粒子加速器，由欧洲核子中心（CERN）在瑞士日内瓦地下建造。LHC的原理是加速质子（氢离子）并让它们相撞，让科学家研究基本粒子和它们之间的相互作用，并在2012年证实了希格斯玻色子的存在。
    {user}: 企鹅会飞吗
    {bot}: 企鹅是不会飞的。企鹅的翅膀短而扁平，更像是游泳时的一对桨。企鹅的身体结构和羽毛密度也更适合在水中游泳，而不是飞行。
    '''
    if background_adv:
      init_prompt = init_prompt + f'\n{user}: ' + background_adv
    init_prompt = init_prompt.strip().split('\n')
    for c in range(len(init_prompt)):
      init_prompt[c] = init_prompt[c].strip().strip('\u3000').strip('\r')
    init_prompt = '\n' + ('\n'.join(init_prompt)).strip() + f"\n{bot}: "
    return init_prompt
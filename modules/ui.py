import os, json
import gradio as gr
from modules.model_utils import ModelUtils
from modules.chat import Chat
#冒险模式
from modules.adventure import Adventure

class UI:

  model_utils = None
  chat_model = None
  adv_model = None
  char_path = './chars'
  adv_path = './adventure'
  config_role_path = './config/config_role.json'
  config_adv_path = './config/config_adv.json'

  def __init__(self, model_utils:ModelUtils):
    self.model_utils = model_utils
    self.chat_model = Chat(model_utils)
    self.adv_model = Adventure(model_utils)

  def get_json_files(self, path):
    files=os.listdir(path)
    file_list = []
    for f in files:
      file_name_arr = f.split('.')
      if file_name_arr[-1] == 'json':
        file_list.append(file_name_arr[0])
    return file_list

  # 更新角色列表
  def update_chars_list(self):
    char_list = self.get_json_files(self.char_path)
    return gr.Dropdown.update(choices=char_list)
  
  def save_config(self, f, top_p, temperature, presence_penalty, frequency_penalty, max_token):
    config = {
      'top_p': top_p, 
      'temperature': temperature, 
      'presence': presence_penalty, 
      'frequency': frequency_penalty,
      'max_token': max_token
    }
    json.dump(config, f, indent=2)

  # 保存角色扮演模式的配置
  def save_config_role(self, top_p=0.7, temperature=2, presence_penalty=0.5, frequency_penalty=0.5):
    with open(self.config_role_path, 'w', encoding='utf8') as f:
      self.save_config(f, top_p, temperature, presence_penalty, frequency_penalty)
    
  # 保存冒险模式的配置
  def save_config_adv(self, top_p=0.7, temperature=2, presence_penalty=0.5, frequency_penalty=0.5):
    with open(self.config_adv_path, 'w', encoding='utf8') as f:
      self.save_config(f, top_p, temperature, presence_penalty, frequency_penalty)
  
  # 保存角色
  def save_char(self, user='', bot='', greeting='', bot_persona=''):
    with open(f"{self.char_path}/{bot}.json", 'w', encoding='utf8') as f:
      json.dump({'user': user, 'bot': bot, 'greeting': greeting, 'bot_persona': bot_persona}, f, indent=2, ensure_ascii=False)
    char_list = self.get_json_files(self.char_path)
    return gr.Dropdown.update(choices=char_list)

  # 载入角色
  def load_char(self, file_name):
    if not file_name:
      raise gr.Error("请选择一个角色")
    with open(f"{self.char_path}/{file_name}.json", 'r', encoding='utf-8') as f:
      char = json.loads(f.read())
    self.chat_model.load_init_prompt(char['user'], char['bot'], char['greeting'], char['bot_persona'])
    chatbot = [[None, char['greeting']]]
    return_arr = (
      char['user'], 
      char['bot'], 
      char['greeting'], 
      char['bot_persona'],
      chatbot, 
      gr.Textbox.update(interactive=True), 
      gr.Button.update(interactive=True), 
      gr.Button.update(interactive=True), 
      gr.Button.update(interactive=True), 
      gr.Button.update(interactive=True), 
      gr.Button.update(interactive=True)
    )
    return return_arr

  # 对话模式中，删除上一次的发言
  def clear_last(self, chatbot):
    message = chatbot[-1][0]
    if(len(chatbot) < 2):
      return chatbot, message
    chatbot = chatbot[0:-1]
    return chatbot, message
  
  def load_adv_story(self, chatbot_adv, top_p_adv, temperature_adv, presence_penalty_adv, frequency_penalty_adv, background_adv):
    flag = False
    if background_adv:
      flag = True
      chatbot_adv = self.adv_model.load_background(chatbot_adv, top_p_adv, temperature_adv, presence_penalty_adv, frequency_penalty_adv, background_adv)
    return_arr = (
      chatbot_adv,
      gr.Textbox.update(interactive=flag),
      gr.Button.update(interactive=flag),
      gr.Button.update(interactive=flag),
      gr.Button.update(interactive=flag)
    )
    return return_arr
    
  def change_adv(self, adv_dropdown):
    if not adv_dropdown:
      return None, None
    with open(f"{self.adv_path}/{adv_dropdown}.json", 'r', encoding='utf-8') as f:
      adv = json.loads(f.read())
    return adv['adv_title'], adv['adv_detail']
  
  def refresh_adv(self):
    adv_list = self.get_json_files(self.adv_path)
    return gr.Dropdown.update(choices=adv_list)
  
  def save_adv(self, adv_title, adv_detail):
    if adv_title and adv_detail:
      with open(f"{self.adv_path}/{adv_title}.json", 'w', encoding='utf8') as f:
        json.dump({'adv_title': adv_title, 'adv_detail': adv_detail}, f, indent=2, ensure_ascii=False)
    adv_list = self.get_json_files(self.adv_path)
    return gr.Dropdown.update(choices=adv_list)
  
  def init_conversation(self):
    self.con_model.init_conversation()
    return_arr = (
      gr.Textbox.update(interactive=True),
      gr.Button.update(interactive=True),
      gr.Button.update(interactive=True),
      gr.Button.update(interactive=True)
    )
    return return_arr

  # 初始化UI
  def init_ui(self):
    with open(self.config_role_path, 'r', encoding='utf-8') as f:
      configs_role = json.loads(f.read())
    with open(self.config_adv_path, 'r', encoding='utf-8') as f:
      configs_adv = json.loads(f.read())
    char_list = self.get_json_files(self.char_path)
    adv_list = self.get_json_files(self.adv_path)
    return_arr = (
      configs_role['top_p'], 
      configs_role['temperature'], 
      configs_role['presence'], 
      configs_role['frequency'], 
      gr.Dropdown.update(choices=char_list), 
      configs_adv['top_p'], 
      configs_adv['temperature'], 
      configs_adv['presence'], 
      configs_adv['frequency'],
      gr.Dropdown.update(choices=adv_list)
    )
    return return_arr

  # 创建UI
  def create_ui(self):
    with gr.Blocks(title="RWKV角色扮演") as app:
      if not os.path.isfile(self.config_role_path):
        self.save_config_role()
      if not os.path.isfile(self.config_adv_path):
        self.save_config_adv()

      with gr.Tab("聊天"):
        with gr.Row():
          with gr.Column(scale=3):
            chatbot = gr.Chatbot(show_label=False).style(height=380)
            message = gr.Textbox(placeholder='说些什么吧', show_label=False, interactive=False)
            with gr.Row():
              with gr.Column(min_width=100):
                submit = gr.Button('提交', interactive=False)
              with gr.Column(min_width=100):
                get_prompt_btn = gr.Button('提词', interactive=False)
            with gr.Row():
              with gr.Column(min_width=100):
                regen = gr.Button('重新生成', interactive=False)
              with gr.Column(min_width=100):
                clear_last_btn = gr.Button('清除上一条', interactive=False)
            delete = gr.Button('清空聊天', interactive=False)
          with gr.Column(scale=1):
            with gr.Row():
              char_dropdown = gr.Dropdown(None, interactive=True, label="请选择角色")
            with gr.Row():
              with gr.Column(min_width=100):
                refresh_char_btn = gr.Button("刷新角色列表")
              with gr.Column(min_width=100):
                load_char_btn = gr.Button("载入角色")
            top_p = gr.Slider(minimum=0, maximum=1.0, step=0.01, label='Top P')
            temperature = gr.Slider(minimum=0.2, maximum=5.0, step=0.01, label='Temperature')
            presence_penalty = gr.Slider(minimum=0, maximum=1, step=0.01, label='Presence Penalty')
            frequency_penalty = gr.Slider(minimum=0, maximum=1, step=0.01, label='Frequency Penalty')
            save_conf = gr.Button('保存设置')

      with gr.Tab("角色"):
        with gr.Row():
          with gr.Column():
            user = gr.Textbox(placeholder='AI怎么称呼你', label='你的名字')
            bot = gr.Textbox(placeholder='角色名字', label='角色的名字')
            greeting = gr.Textbox(placeholder='开场白', label='开场白')
          with gr.Column():
            bot_persona = gr.TextArea(placeholder='角色性格', label='角色的性格', lines=10)
        save_char_btn = gr.Button('保存角色')
      
      input_list = [message, chatbot, top_p, temperature, presence_penalty, frequency_penalty, user, bot]
      output_list = [message, chatbot]
      char_input_list = [user, bot, greeting, bot_persona, chatbot]
      interactive_list = [message, submit, regen, delete, clear_last_btn, get_prompt_btn]

      load_char_btn.click(self.load_char, inputs=[char_dropdown], outputs=char_input_list + interactive_list)
      refresh_char_btn.click(self.update_chars_list, outputs=[char_dropdown])
      save_conf.click(self.save_config_role, inputs=input_list[2:6])
      message.submit(self.chat_model.on_message, inputs=input_list, outputs=output_list)
      submit.click(self.chat_model.on_message, inputs=input_list, outputs=output_list)
      regen.click(self.chat_model.regen_msg, inputs=input_list[1:], outputs=output_list)
      delete.click(self.chat_model.reset_bot, inputs=[greeting], outputs=output_list)
      save_char_btn.click(self.save_char, inputs=char_input_list[:-1], outputs=[char_dropdown])
      clear_last_btn.click(self.clear_last, inputs=[chatbot], outputs=[chatbot, message])
      get_prompt_btn.click(self.chat_model.get_prompt, inputs=input_list[2:], outputs=[message])

      with gr.Tab('冒险'):
        with gr.Row():
          with gr.Column(scale=3):
            chatbot_adv = gr.Chatbot(show_label=False).style(height=380)
            message_adv = gr.Textbox(placeholder='请描述你的行动', show_label=False, interactive=False)
            with gr.Row():
              with gr.Column(min_width=100):
                submit_adv = gr.Button('提交', interactive=False)
              with gr.Column(min_width=100):
                regen_adv = gr.Button('重新生成', interactive=False)
            delete_adv = gr.Button('清空冒险', interactive=False)
          with gr.Column(scale=1):
            adv_dropdown = gr.Dropdown(None, interactive=True, label="请选择冒险故事")
            refresh_adv_btn = gr.Button("刷新故事列表")
            adv_title = gr.Textbox(placeholder='请输入故事标题', label='故事标题')
            adv_detail = gr.TextArea(placeholder='请输入故事背景', interactive=True, label='故事背景', lines=5)
            with gr.Row():
              with gr.Column(min_width=100):
                load_adv_btn = gr.Button('开始冒险')
              with gr.Column(min_width=100):
                save_adv_btn = gr.Button('保存故事')
        with gr.Row():
          top_p_adv = gr.Slider(minimum=0, maximum=1.0, step=0.01, value=0.6, label='Top P')
          temperature_adv = gr.Slider(minimum=0.2, maximum=5.0, step=0.01, value=1, label='Temperature')
          presence_penalty_adv = gr.Slider(minimum=0, maximum=1, step=0.01, value=0.5, label='Presence Penalty')
          frequency_penalty_adv = gr.Slider(minimum=0, maximum=1, step=0.01, value=0.5, label='Frequency Penalty')
        with gr.Row():
          save_conf_adv = gr.Button('保存设置')
      adv_input_list = [message_adv, chatbot_adv, top_p_adv, temperature_adv, presence_penalty_adv, frequency_penalty_adv, adv_detail]
      adv_output_list = [message_adv, chatbot_adv]
      adv_interactive_list = [message_adv, submit_adv, regen_adv, delete_adv]
      load_adv_btn.click(self.load_adv_story, inputs=adv_input_list[1:], outputs=[chatbot_adv] + adv_interactive_list)
      message_adv.submit(self.adv_model.on_message_adv, inputs=adv_input_list[:-1], outputs=adv_output_list)
      submit_adv.click(self.adv_model.on_message_adv, inputs=adv_input_list[:-1], outputs=adv_output_list)
      regen_adv.click(self.adv_model.regen_msg_adv, inputs=adv_input_list[1:-1], outputs=[chatbot_adv])
      delete_adv.click(self.adv_model.reset_adv, outputs=adv_output_list)
      save_conf_adv.click(self.save_config_adv, inputs=adv_input_list[2:6])
      adv_dropdown.change(self.change_adv, inputs=[adv_dropdown], outputs=[adv_title, adv_detail])
      refresh_adv_btn.click(self.refresh_adv, outputs=[adv_dropdown])
      save_adv_btn.click(self.save_adv, inputs=[adv_title, adv_detail], outputs=[adv_dropdown])

      reload_list = [
        top_p, 
        temperature, 
        presence_penalty, 
        frequency_penalty, 
        char_dropdown, 
        top_p_adv, 
        temperature_adv, 
        presence_penalty_adv, 
        frequency_penalty_adv, 
        adv_dropdown
      ]
      app.load(self.init_ui, outputs=reload_list)

    return app
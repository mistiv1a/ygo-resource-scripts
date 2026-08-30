import json
import os
import urllib.request

SUPER_PRE_URL = 'https://cdncf.moecube.com/ygopro-super-pre/data/test-release-v2.json'

j = None
with open('cards.json') as fp:
    j = json.load(fp)

with urllib.request.urlopen(SUPER_PRE_URL, timeout=30) as response:
    super_pre = json.load(response)

def list_files(directory):
  files = os.listdir(directory)
  return [file for file in files if not os.path.isdir(os.path.join(directory, file))]

fin_set = set(list_files('./cardtext-fin'))
for k in j:
    v = j[k]
    if v['id'] == 0:
        continue
    if str(v['id']) + '.txt' in fin_set:
        continue
    s = ''
    s += v['cn_name'] + '\n'
    if "set_ext" in v:
        s += '（系列：' + v['set_ext'] + '）\n'
    types = v['text']['types']
    types = types.replace('☆', '阶级').replace('★', '等级')
    s += types + '\n'
    if 'pdesc' in v['text'] and len(v['text']['pdesc']) > 0:
        s += '---\n' + v['text']['pdesc'].replace('\r', '').strip() + '\n---\n'
    s += v['text']['desc'].replace('\r', '')
    with open('cardtext/' + str(v['id']) + '.txt', 'w') as fp:
        fp.write(s)

for v in super_pre:
    card_id = str(v['id'])
    if card_id + '.txt' in fin_set:
        continue
    s = v['name'] + '\n'
    types = v['overallString'].replace('☆', '阶级').replace('★', '等级')
    s += types + '\n'
    s += v['desc'].replace('\r', '')
    with open('cardtext/' + card_id + '.txt', 'w') as fp:
        fp.write(s)

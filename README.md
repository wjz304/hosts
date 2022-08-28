# hosts

Linux:
```
# 删除
sudo sed -i '/# ING Hosts Start/,/# ING Hosts End/d' /etc/hosts
# 添加
curl -s -L https://raw.githubusercontent.com/wjz304/hosts/main/hosts | sudo tee -a /etc/hosts
```

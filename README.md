# hosts  

## Note  
每日自动更新 github 和 tinyMediaManager 的 IP 地址。  

## Used  
Windows/MacOS:  
```
推荐使用下面 SwitchHosts, 官网查看：https://swh.app/zh
```
Linux:
```
# 删除
sudo sed -i '/# ING Hosts Start/,/# ING Hosts End/d' /etc/hosts
# 添加
curl -s -L https://raw.githubusercontent.com/wjz304/hosts/main/hosts | sudo tee -a /etc/hosts
```

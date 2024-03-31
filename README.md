# hosts  

## Note  
每日自动更新 github, docker 和 tinyMediaManager 的 IP 地址。  

hosts Url:   
Raw Url: https://raw.githubusercontent.com/wjz304/hosts/main/hosts  
CDN Url: https://gcore.jsdelivr.net/gh/wjz304/hosts@main/hosts  
CDN Url: https://cdn.staticaly.com/gh/wjz304/hosts/main/hosts    (推荐)  

## Used  
Windows/MacOS:  
```
推荐使用 SwitchHosts, 官网查看：https://swh.app/zh
```
![image](https://user-images.githubusercontent.com/5615843/187586697-201b444c-1a3b-486a-867d-5fff9e63a4b2.png)

Linux:
```
# 删除
sudo sed -i '/# ING Hosts Start/,/# ING Hosts End/d' /etc/hosts
# 添加
curl -s -k -L https://raw.githubusercontent.com/wjz304/hosts/main/hosts | sudo tee -a /etc/hosts
# 重启网络
/etc/init.d/network restart
```

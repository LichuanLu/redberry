__author__ = 'chengc017'
# coding: utf-8
import hashlib,datetime,random

def generatorVerifyCode():
    mp = hashlib.md5()
    mp.update(str(datetime.datetime.now())+str(random.random()))
    mp_src = mp.hexdigest()
    rand_str = mp_src[0:6]
    return rand_str

if  __name__ == '__main__':
    print generatorVerifyCode()
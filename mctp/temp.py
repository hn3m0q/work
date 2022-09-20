def kkk(v=1):
    locals().update([[v,"myvalue"]])
    locals()['v'] = 5
    globals()['v'] = 2
    print(locals().keys())
    print(v)

kkk()
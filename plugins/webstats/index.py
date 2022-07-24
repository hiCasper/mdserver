# coding:utf-8

import sys
import io
import os
import time
import json

sys.path.append(os.getcwd() + "/class/core")
import mw


app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'webstats'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


sys.path.append(getPluginDir() + "/class")
from LuaMaker import LuaMaker


def listToLuaFile(path, lists):
    content = LuaMaker.makeLuaTable(lists)
    content = "return " + content
    mw.writeFile(path, content)


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getConf():
    conf = getServerDir() + "/lua/config.json"
    return conf


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def luaConf():
    return mw.getServerDir() + '/web_conf/nginx/vhost/webstats.conf'


def status():
    path = luaConf()
    if not os.path.exists(path):
        return 'stop'
    return 'start'


def loadLuaLogFile():
    lua_dir = getServerDir() + "/lua"
    lua_dst = lua_dir + "/webstats_log.lua"

    lua_tpl = getPluginDir() + '/lua/webstats_log.lua'
    content = mw.readFile(lua_tpl)
    content = content.replace('{$SERVER_APP}', getServerDir())
    content = content.replace('{$ROOT_PATH}', mw.getServerDir())
    mw.writeFile(lua_dst, content)


def loadConfigFile():
    lua_dir = getServerDir() + "/lua"
    conf_tpl = getPluginDir() + "/conf/config.json"

    content = mw.readFile(conf_tpl)
    content = json.loads(content)

    dst_conf_json = getServerDir() + "/lua/config.json"
    mw.writeFile(dst_conf_json, json.dumps(content))

    dst_conf_lua = getServerDir() + "/lua/config.lua"
    listToLuaFile(dst_conf_lua, content)


def loadLuaSiteFile():
    lua_dir = getServerDir() + "/lua"

    content = makeSiteConfig()
    for index in range(len(content)):
        pSqliteDb('web_log', content[index]['name'])

    lua_site_json = lua_dir + "/sites.json"
    mw.writeFile(lua_site_json, json.dumps(content))

    # 设置默认列表
    default_json = lua_dir + "/default.json"
    ddata = {}
    dlist = []
    for i in content:
        dlist.append(i["name"])

    dlist.append('unset')
    ddata["list"] = dlist
    if len(ddata["list"]) < 1:
        ddata["default"] = "unset"
    else:
        ddata["default"] = dlist[0]
    mw.writeFile(default_json, json.dumps(ddata))

    lua_site = lua_dir + "/sites.lua"
    listToLuaFile(lua_site, content)


def loadDebugLogFile():
    debug_log = getServerDir() + "/debug.log"
    lua_dir = getServerDir() + "/lua"
    mw.writeFile(debug_log, '')


def pSqliteDb(dbname='web_logs', site_name='unset'):

    db_dir = getServerDir() + '/logs/' + site_name
    if not os.path.exists(db_dir):
        mw.execShell('mkdir -p ' + db_dir)

    name = 'logs'
    file = db_dir + '/' + name + '.db'

    if not os.path.exists(file):
        conn = mw.M(dbname).dbPos(db_dir, name)
        sql = mw.readFile(getPluginDir() + '/conf/init.sql')
        sql_list = sql.split(';')
        for index in range(len(sql_list)):
            conn.execute(sql_list[index], ())
    else:
        conn = mw.M(dbname).dbPos(db_dir, name)

    return conn


def makeSiteConfig():
    siteM = mw.M('sites')
    domainM = mw.M('domain')
    slist = siteM.field('id,name').where(
        'status=?', (1,)).order('id desc').select()

    data = []
    for s in slist:
        tmp = {}
        tmp['name'] = s['name']

        dlist = domainM.field('id,name').where(
            'pid=?', (s['id'],)).order('id desc').select()

        _t = []
        for d in dlist:
            _t.append(d['name'])

        tmp['domains'] = _t
        data.append(tmp)

    return data


def initDreplace():

    service_path = getServerDir()

    pSqliteDb()

    path = luaConf()
    path_tpl = getPluginDir() + '/conf/webstats.conf'
    if not os.path.exists(path):
        content = mw.readFile(path_tpl)
        content = content.replace('{$SERVER_APP}', service_path)
        content = content.replace('{$ROOT_PATH}', mw.getServerDir())
        mw.writeFile(path, content)

    lua_dir = getServerDir() + "/lua"
    if not os.path.exists(lua_dir):
        mw.execShell('mkdir -p ' + lua_dir)

    log_path = getServerDir() + "/logs"
    if not os.path.exists(log_path):
        mw.execShell('mkdir -p ' + log_path)

    loadLuaLogFile()
    loadConfigFile()
    loadLuaSiteFile()
    loadDebugLogFile()

    return 'ok'


def start():
    initDreplace()

    if not mw.isAppleSystem():
        mw.execShell("chown -R www:www " + getServerDir())

    mw.restartWeb()
    return 'ok'


def stop():
    path = luaConf()
    os.remove(path)
    mw.restartWeb()
    return 'ok'


def restart():
    initDreplace()
    return 'ok'


def reload():
    initDreplace()

    loadLuaLogFile()
    loadDebugLogFile()
    mw.restartWeb()
    return 'ok'


def getGlobalConf():
    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)
    return mw.returnJson(True, 'ok', content)


def setGlobalConf():
    args = getArgs()

    conf = getConf()
    content = mw.readFile(conf)
    content = json.loads(content)

    for v in ['record_post_args', 'record_get_403_args']:
        data = checkArgs(args, [v])
        if data[0]:
            rval = False
            if args[v] == "true":
                rval = True
            content['global'][v] = rval

    for v in ['ip_top_num', 'uri_top_num', 'save_day']:
        data = checkArgs(args, [v])
        if data[0]:
            content['global'][v] = int(args[v])

    for v in ['cdn_headers', 'exclude_extension', 'exclude_status', 'exclude_ip']:
        data = checkArgs(args, [v])
        if data[0]:
            content['global'][v] = args[v].split("\\n")

    data = checkArgs(args, ['exclude_url'])
    if data[0]:
        exclude_url = args['exclude_url'].strip(";")
        exclude_url_val = []
        if exclude_url != "":
            exclude_url_list = exclude_url.split(";")
            for i in exclude_url_list:
                t = i.split("|")
                val = {}
                val['mode'] = t[0]
                val['url'] = t[1]
                exclude_url_val.append(val)
        content['global']['exclude_url'] = exclude_url_val

    mw.writeFile(conf, json.dumps(content))
    conf_lua = getServerDir() + "/lua/config.lua"
    listToLuaFile(conf_lua, content)
    mw.restartWeb()
    return mw.returnJson(True, '设置成功')


def getDefaultSite():
    lua_dir = getServerDir() + "/lua"
    path = lua_dir + "/default.json"
    data = mw.readFile(path)
    return mw.returnJson(True, 'OK', json.loads(data))


def setDefaultSite(name):
    lua_dir = getServerDir() + "/lua"
    path = lua_dir + "/default.json"
    data = mw.readFile(path)
    data = json.loads(data)
    data['default'] = name
    mw.writeFile(path, json.dumps(data))
    return mw.returnJson(True, 'OK')


def getLogsList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'method', 'status_code', 'spider_type', 'query_date', 'search_uri'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    method = args['method']
    status_code = args['status_code']
    spider_type = args['spider_type']
    query_date = args['query_date']
    search_uri = args['search_uri']
    setDefaultSite(domain)

    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    conn = pSqliteDb('web_logs', domain)

    field = 'time,ip,domain,server_name,method,protocol,status_code,request_headers,ip_list,client_port,body_length,user_agent,referer,request_time,uri,body_length'
    condition = ''
    conn = conn.field(field)
    conn = conn.where("1=1", ())

    if method != "all":
        conn = conn.andWhere("method=?", (method,))

    if status_code != "all":
        conn = conn.andWhere("status_code=?", (status_code,))

    if spider_type == "normal":
        pass
    elif spider_type == "only_spider":
        conn = conn.andWhere("is_spider>?", (0,))
    elif spider_type == "no_spider":
        conn = conn.andWhere("is_spider=?", (0,))
    elif int(spider_type) > 0:
        conn = conn.andWhere("is_spider=?", (spider_type,))

    todayTime = time.strftime('%Y-%m-%d 00:00:00', time.localtime())
    todayUt = int(time.mktime(time.strptime(todayTime, "%Y-%m-%d %H:%M:%S")))
    if query_date == 'today':
        conn = conn.andWhere("time>=?", (todayUt,))
    elif query_date == "yesterday":
        conn = conn.andWhere("time>=? and time<=?", (todayUt - 86400, todayUt))
    elif query_date == "l7":
        conn = conn.andWhere("time>=?", (todayUt - 7 * 86400,))
    elif query_date == "l30":
        conn = conn.andWhere("time>=?", (todayUt - 30 * 86400,))
    else:
        exlist = query_date.split("-")
        conn = conn.andWhere("time>=? and time<=?", (exlist[0], exlist[1]))

    if search_uri != "":
        conn = conn.andWhere("uri like '%" + search_uri + "%'", ())

    clist = conn.limit(limit).order('time desc').inquiry()
    count_key = "count(*) as num"
    count = conn.field(count_key).limit('').order('').inquiry()
    # print(count)
    count = count[0][count_key]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    return mw.returnJson(True, 'ok', data)


def getLogsErrorList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'status_code', 'query_date'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    status_code = args['status_code']
    query_date = args['query_date']
    setDefaultSite(domain)

    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    conn = pSqliteDb('web_logs', domain)

    field = 'time,ip,domain,server_name,method,protocol,status_code,ip_list,client_port,body_length,user_agent,referer,request_time,uri,body_length'
    conn = conn.field(field)
    conn = conn.where("1=1", ())

    if status_code != "all":
        if status_code.find("x") > -1:
            status_code = status_code.replace("x", "%")
            conn = conn.andWhere("status_code like ?", (status_code,))
        else:
            conn = conn.andWhere("status_code=?", (status_code,))
    else:
        conn = conn.andWhere(
            "(status_code like '50%' or status_code like '40%')", ())

    todayTime = time.strftime('%Y-%m-%d 00:00:00', time.localtime())
    todayUt = int(time.mktime(time.strptime(todayTime, "%Y-%m-%d %H:%M:%S")))
    if query_date == 'today':
        conn = conn.andWhere("time>=?", (todayUt,))
    elif query_date == "yesterday":
        conn = conn.andWhere("time>=? and time<=?", (todayUt - 86400, todayUt))
    elif query_date == "l7":
        conn = conn.andWhere("time>=?", (todayUt - 7 * 86400,))
    elif query_date == "l30":
        conn = conn.andWhere("time>=?", (todayUt - 30 * 86400,))
    else:
        exlist = query_date.split("-")
        conn = conn.andWhere("time>=? and time<=?", (exlist[0], exlist[1]))

    clist = conn.limit(limit).order('time desc').inquiry()
    count_key = "count(*) as num"
    count = conn.field(count_key).limit('').order('').inquiry()
    count = count[0][count_key]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    return mw.returnJson(True, 'ok', data)


def toSumField(sql):
    l = sql.split(",")
    field = ""
    for x in l:
        field += "sum(" + x + ") as " + x + ","
    field = field.strip(',')
    return field


def getClientStatList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'query_date'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    query_date = args['query_date']
    setDefaultSite(domain)

    conn = pSqliteDb('client_stat', domain)
    stat = pSqliteDb('client_stat', domain)

    # 列表
    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    field = 'time,weixin,android,iphone,mac,windows,linux,edeg,firefox,msie,metasr,qh360,theworld,tt,maxthon,opera,qq,uc,pc2345,safari,chrome,machine,mobile,other'
    field_sum = toSumField(field.replace("time,", ""))
    time_field = "substr(time,1,8),"
    field_sum = time_field + field_sum

    stat = stat.field(field_sum)
    if query_date == "today":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 0 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "yesterday":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 1 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "l7":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 7 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "l30":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 30 * 86400))
        stat.where("time >= ?", (todayTime,))
    else:
        exlist = query_date.split("-")
        start = time.strftime(
            '%Y%m%d00', time.localtime(int(exlist[0])))
        end = time.strftime(
            '%Y%m%d23', time.localtime(int(exlist[1])))
        stat.where("time >= ? and time <= ? ", (start, end,))

    # 图表数据
    statlist = stat.group('substr(time,1,4)').inquiry(field)

    if len(statlist) > 0:
        del(statlist[0]['time'])

        pc = 0
        pc_key_list = ['chrome', 'qh360', 'edeg', 'firefox', 'safari', 'msie',
                       'metasr', 'theworld', 'tt', 'maxthon', 'opera', 'qq', 'pc2345']

        for x in pc_key_list:
            pc += statlist[0][x]

        mobile = 0
        mobile_key_list = ['mobile', 'android', 'iphone', 'weixin']
        for x in mobile_key_list:
            mobile += statlist[0][x]
        reqest_total = pc + mobile

        sum_data = {
            "pc": pc,
            "mobile": mobile,
            "reqest_total": reqest_total,
        }

        statlist = sorted(statlist[0].items(),
                          key=lambda x: x[1], reverse=True)
        _statlist = statlist[0:10]
        __statlist = {}
        statlist = []
        for x in _statlist:
            __statlist[x[0]] = x[1]
        statlist.append(__statlist)
    else:
        sum_data = {
            "pc": 0,
            "mobile": 0,
            "reqest_total": 0,
        }
        statlist = []

    # 列表数据
    conn = conn.field(field_sum)
    clist = conn.group('substr(time,1,8)').limit(
        limit).order('time desc').inquiry(field)

    sql = "SELECT count(*) num from (\
            SELECT count(*) as num FROM client_stat GROUP BY substr(time,1,8)\
        )"
    result = conn.query(sql, ())
    result = list(result)
    count = result[0][0]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist
    data['stat_list'] = statlist
    data['sum_data'] = sum_data

    return mw.returnJson(True, 'ok', data)


def getSpiderStatList():
    args = getArgs()
    check = checkArgs(args, ['page', 'page_size',
                             'site', 'query_date'])
    if not check[0]:
        return check[1]

    page = int(args['page'])
    page_size = int(args['page_size'])
    domain = args['site']
    tojs = args['tojs']
    query_date = args['query_date']
    setDefaultSite(domain)

    conn = pSqliteDb('spider_stat', domain)
    stat = pSqliteDb('spider_stat', domain)

    # 列表
    limit = str(page_size) + ' offset ' + str(page_size * (page - 1))
    field = 'time,weixin,android,iphone,mac,windows,linux,edeg,firefox,msie,metasr,qh360,theworld,tt,maxthon,opera,qq,uc,pc2345,safari,chrome,machine,mobile,other'
    field_sum = toSumField(field.replace("time,", ""))
    time_field = "substr(time,1,8),"
    field_sum = time_field + field_sum

    stat = stat.field(field_sum)
    if query_date == "today":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 0 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "yesterday":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 1 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "l7":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 7 * 86400))
        stat.where("time >= ?", (todayTime,))
    elif query_date == "l30":
        todayTime = time.strftime(
            '%Y%m%d00', time.localtime(time.time() - 30 * 86400))
        stat.where("time >= ?", (todayTime,))
    else:
        exlist = query_date.split("-")
        start = time.strftime(
            '%Y%m%d00', time.localtime(int(exlist[0])))
        end = time.strftime(
            '%Y%m%d23', time.localtime(int(exlist[1])))
        stat.where("time >= ? and time <= ? ", (start, end,))

    # 图表数据
    statlist = stat.group('substr(time,1,4)').inquiry(field)

    if len(statlist) > 0:
        del(statlist[0]['time'])

        pc = 0
        pc_key_list = ['chrome', 'qh360', 'edeg', 'firefox', 'safari', 'msie',
                       'metasr', 'theworld', 'tt', 'maxthon', 'opera', 'qq', 'pc2345']

        for x in pc_key_list:
            pc += statlist[0][x]

        mobile = 0
        mobile_key_list = ['mobile', 'android', 'iphone', 'weixin']
        for x in mobile_key_list:
            mobile += statlist[0][x]
        reqest_total = pc + mobile

        sum_data = {
            "pc": pc,
            "mobile": mobile,
            "reqest_total": reqest_total,
        }

        statlist = sorted(statlist[0].items(),
                          key=lambda x: x[1], reverse=True)
        _statlist = statlist[0:10]
        __statlist = {}
        statlist = []
        for x in _statlist:
            __statlist[x[0]] = x[1]
        statlist.append(__statlist)
    else:
        sum_data = {
            "pc": 0,
            "mobile": 0,
            "reqest_total": 0,
        }
        statlist = []

    # 列表数据
    conn = conn.field(field_sum)
    clist = conn.group('substr(time,1,8)').limit(
        limit).order('time desc').inquiry(field)

    sql = "SELECT count(*) num from (\
            SELECT count(*) as num FROM client_stat GROUP BY substr(time,1,8)\
        )"
    result = conn.query(sql, ())
    result = list(result)
    count = result[0][0]

    data = {}
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = tojs
    data['page'] = mw.getPage(_page)
    data['data'] = clist
    data['stat_list'] = statlist
    data['sum_data'] = sum_data

    return mw.returnJson(True, 'ok', data)

if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'run_info':
        print(runInfo())
    elif func == 'get_global_conf':
        print(getGlobalConf())
    elif func == 'set_global_conf':
        print(setGlobalConf())
    elif func == 'get_default_site':
        print(getDefaultSite())
    elif func == 'get_logs_list':
        print(getLogsList())
    elif func == 'get_logs_error_list':
        print(getLogsErrorList())
    elif func == 'get_client_stat_list':
        print(getClientStatList())
    elif func == 'get_spider_stat_list':
        print(getSpiderStatList())
    else:
        print('error')

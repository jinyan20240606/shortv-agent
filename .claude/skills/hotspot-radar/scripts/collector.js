/**
 * 热点雷达 - 数据采集器 v5
 * 微博: 官方API (weibo.com)
 * B站: 官方API (api.bilibili.com)
 * 抖音: 官方API (douyin.com)
 * 知乎: 官方API (需 cookie 鉴权，通过环境变量 ZHI_HU_COOKIE 注入)
 * 小红书: 官方API (需 cookie 鉴权，通过环境变量 XHS_COOKIE 注入)
 *
 * 注意：知乎/小红书官方接口需要登录 cookie；未提供 cookie 时返回空并标注数据源需鉴权。
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// 配置
const CONFIG = {
  dataDir: path.join(__dirname, '../data'),
  historyDir: path.join(__dirname, '../data/history'),
  configDir: path.join(__dirname, '../config'),
  // API接口地址
  API: {
    // 微博官方API
    WEIBO: 'https://weibo.com/ajax/statuses/hot_band',
    // B站官方排行榜API
    BILIBILI: 'https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all',
    // 抖音官方热搜API
    DOUYIN: 'https://www.douyin.com/aweme/v1/web/hot/search/list/',
    // 知乎官方热榜API（需 cookie）
    ZHIHU: 'https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50&desktop=true',
    // 小红书官方热榜API（需 cookie）
    XIAOHONGSHU: 'https://edith.xiaohongshu.com/api/sns/web/v1/hot/search',
  }
};

// 确保目录存在
function ensureDirs() {
  var dirs = [
    CONFIG.dataDir,
    CONFIG.historyDir,
    path.join(CONFIG.historyDir, 'weibo'),
    path.join(CONFIG.historyDir, 'zhihu'),
    path.join(CONFIG.historyDir, 'bilibili'),
    path.join(CONFIG.historyDir, 'douyin'),
    path.join(CONFIG.historyDir, 'xiaohongshu'),
    path.join(CONFIG.dataDir, 'trends'),
    CONFIG.configDir,
  ];
  dirs.forEach(function(dir) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });
}

// HTTP请求封装（支持自定义 headers）
function fetch(url, options) {
  return new Promise(function(resolve, reject) {
    var protocol = url.startsWith('https') ? https : require('http');
    var headers = Object.assign({
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'application/json, text/plain, */*',
    }, (options && options.headers) || {});

    var requestOptions = {
      headers: headers,
      timeout: 15000,
    };

    protocol.get(url, requestOptions, function(res) {
      var data = '';
      res.on('data', function(chunk) { data += chunk; });
      res.on('end', function() {
        var contentType = res.headers['content-type'] || '';
        if (contentType.indexOf('json') !== -1) {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            resolve({ raw: data });
          }
        } else {
          // 非 JSON 响应，尝试解析，失败则返回原始内容标记
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            resolve({ raw: data, statusCode: res.statusCode });
          }
        }
      });
    }).on('error', function(err) {
      reject(err);
    });
  });
}

// 获取微博热搜
async function fetchWeibo() {
  try {
    console.log('  [微博] 开始获取...');
    var data = await fetch(CONFIG.API.WEIBO, {
      headers: { 'Referer': 'https://weibo.com' }
    });
    var items = data.data && data.data.band_list ? data.data.band_list : [];
    var result = items.map(function(item, idx) {
      return {
        rank: idx + 1,
        topic: item.word || item.topic_name,
        hotValue: item.raw_hot || item.num || 0,
        label: item.label_name || '',
        url: 'https://s.weibo.com/weibo?q=' + encodeURIComponent(item.word || item.topic_name)
      };
    });
    console.log('  [微博] 获取成功: ' + result.length + '条');
    return result;
  } catch (e) {
    console.log('  [微博] 获取失败: ' + e.message);
    return [];
  }
}

// 获取B站热搜 - 官方排行榜API
async function fetchBilibili() {
  try {
    console.log('  [B站] 开始获取...');
    var data = await fetch(CONFIG.API.BILIBILI, {
      headers: { 'Referer': 'https://www.bilibili.com/' }
    });
    if (data.code === 0 && data.data && Array.isArray(data.data.list)) {
      var result = data.data.list.map(function(item, idx) {
        return {
          rank: idx + 1,
          topic: item.title || '',
          hotValue: (item.stat && item.stat.view) || 0,
          label: (item.tname) || '',
          url: item.short_link_v2 || ('https://www.bilibili.com/video/' + item.bvid)
        };
      });
      console.log('  [B站] 获取成功: ' + result.length + '条');
      return result;
    }
    console.log('  [B站] 接口返回异常');
    return [];
  } catch (e) {
    console.log('  [B站] 获取失败: ' + e.message);
    return [];
  }
}

// 获取抖音热搜 - 官方热搜API
async function fetchDouyin() {
  try {
    console.log('  [抖音] 开始获取...');
    var data = await fetch(CONFIG.API.DOUYIN, {
      headers: { 'Referer': 'https://www.douyin.com/' }
    });
    if (data.data && Array.isArray(data.data.word_list)) {
      var result = data.data.word_list.map(function(item, idx) {
        return {
          rank: item.rank || idx + 1,
          topic: item.word || '',
          hotValue: item.hot_value || 0,
          label: item.label_name || '',
          url: item.url || ''
        };
      });
      console.log('  [抖音] 获取成功: ' + result.length + '条');
      return result;
    }
    console.log('  [抖音] 接口返回异常');
    return [];
  } catch (e) {
    console.log('  [抖音] 获取失败: ' + e.message);
    return [];
  }
}

// 获取知乎热搜 - 官方API（需 cookie，从环境变量 ZHI_HU_COOKIE 注入）
async function fetchZhihu() {
  try {
    console.log('  [知乎] 开始获取...');
    var cookie = process.env.ZHI_HU_COOKIE || '';
    if (!cookie) {
      console.log('  [知乎] 跳过：未配置 ZHI_HU_COOKIE（官方接口需登录 cookie）');
      return [];
    }
    var data = await fetch(CONFIG.API.ZHIHU, {
      headers: { 'Referer': 'https://www.zhihu.com/hot', 'Cookie': cookie }
    });
    if (data.data && Array.isArray(data.data)) {
      var result = data.data.map(function(item, idx) {
        var target = item.target || {};
        return {
          rank: idx + 1,
          topic: target.title || item.title || '',
          hotValue: item.detail_text || 0,
          label: item.detail_text || '',
          url: target.url || ''
        };
      });
      console.log('  [知乎] 获取成功: ' + result.length + '条');
      return result;
    }
    console.log('  [知乎] 接口返回异常（cookie 可能失效或接口变更）');
    return [];
  } catch (e) {
    console.log('  [知乎] 获取失败: ' + e.message);
    return [];
  }
}

// 获取小红书热搜 - 官方API（需 cookie，从环境变量 XHS_COOKIE 注入）
async function fetchXiaohongshu() {
  try {
    console.log('  [小红书] 开始获取...');
    var cookie = process.env.XHS_COOKIE || '';
    if (!cookie) {
      console.log('  [小红书] 跳过：未配置 XHS_COOKIE（官方接口需登录 cookie）');
      return [];
    }
    var data = await fetch(CONFIG.API.XIAOHONGSHU, {
      headers: { 'Referer': 'https://www.xiaohongshu.com/', 'Cookie': cookie }
    });
    if (data.data && Array.isArray(data.data.items)) {
      var result = data.data.items.map(function(item, idx) {
        var note = item.note_card || item;
        return {
          rank: idx + 1,
          topic: note.display_title || note.title || '',
          hotValue: (note.interact_info && note.interact_info.liked_count) || 0,
          label: note.type || '',
          url: 'https://www.xiaohongshu.com/explore/' + (note.note_id || '')
        };
      });
      console.log('  [小红书] 获取成功: ' + result.length + '条');
      return result;
    }
    console.log('  [小红书] 接口返回异常（cookie 可能失效或接口变更）');
    return [];
  } catch (e) {
    console.log('  [小红书] 获取失败: ' + e.message);
    return [];
  }
}

// 获取所有平台热榜
async function fetchAll() {
  console.log('\n开始采集全网热榜...\n');

  var results = await Promise.all([
    fetchWeibo(),
    fetchZhihu(),
    fetchBilibili(),
    fetchDouyin(),
    fetchXiaohongshu()
  ]);

  var data = {
    weibo: results[0] || [],
    zhihu: results[1] || [],
    bilibili: results[2] || [],
    douyin: results[3] || [],
    xiaohongshu: results[4] || [],
    timestamp: new Date().toISOString()
  };

  console.log('\n采集完成:', {
    weibo: data.weibo.length,
    zhihu: data.zhihu.length,
    bilibili: data.bilibili.length,
    douyin: data.douyin.length,
    xiaohongshu: data.xiaohongshu.length
  });

  return data;
}

// 保存历史数据
function saveHistory(data) {
  var today = new Date().toISOString().split('T')[0];
  var platforms = ['weibo', 'zhihu', 'bilibili', 'douyin', 'xiaohongshu'];

  platforms.forEach(function(platform) {
    var filePath = path.join(CONFIG.historyDir, platform, today + '.json');
    fs.writeFileSync(filePath, JSON.stringify(data[platform], null, 2), 'utf-8');
  });

  // 保存完整快照
  var snapshotPath = path.join(CONFIG.dataDir, 'trends', today + '.json');
  fs.writeFileSync(snapshotPath, JSON.stringify(data, null, 2), 'utf-8');

  console.log('历史数据已保存: ' + today);
}

// 主函数
async function main() {
  ensureDirs();
  var data = await fetchAll();
  saveHistory(data);

  console.log('\n========== 今日热榜汇总 ==========');
  console.log('- 微博: ' + data.weibo.length + '条');
  console.log('- 知乎: ' + data.zhihu.length + '条（需 ZHI_HU_COOKIE）');
  console.log('- B站: ' + data.bilibili.length + '条');
  console.log('- 抖音: ' + data.douyin.length + '条');
  console.log('- 小红书: ' + data.xiaohongshu.length + '条（需 XHS_COOKIE）');
  console.log('================================\n');

  return data;
}

// 导出
module.exports = {
  fetchAll: fetchAll,
  saveHistory: saveHistory,
  fetchWeibo: fetchWeibo,
  fetchZhihu: fetchZhihu,
  fetchBilibili: fetchBilibili,
  fetchDouyin: fetchDouyin,
  fetchXiaohongshu: fetchXiaohongshu,
  ensureDirs: ensureDirs,
  main: main
};

// 直接运行
if (require.main === module) {
  main().then(function(data) {
    console.log('数据采集完成');
    process.exit(0);
  }).catch(function(e) {
    console.error('采集失败:', e);
    process.exit(1);
  });
}

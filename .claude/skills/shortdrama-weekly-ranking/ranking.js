"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getWeeklyRanking = getWeeklyRanking;
const axios_1 = __importDefault(require("axios"));
const cheerio = __importStar(require("cheerio"));
// === 方案1：搜狗微信搜索 "短剧周榜" ===
// 搜狗微信搜索可抓取，返回微信公众号文章列表
// 从文章标题和摘要中提取短剧信息
async function fetchFromWechatSearch() {
    const items = [];
    const sources = [];
    try {
        const url = `https://weixin.sogou.com/weixin?type=2&query=${encodeURIComponent('短剧周榜')}`;
        const res = await axios_1.default.get(url, {
            timeout: 10000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        });
        const $ = cheerio.load(res.data);
        sources.push('搜狗微信');
        // 提取微信公众号文章标题和摘要
        $('.txt-box').each((_, el) => {
            const title = $(el).find('h3 a').text().trim();
            const summary = $(el).find('.str_info').text().trim();
            const fullText = `${title} ${summary}`;
            // 从标题/摘要中提取剧名（书名号内的内容）
            const dramaMatches = fullText.match(/[《]([^》]{2,15})[》]/g);
            if (dramaMatches) {
                for (const match of dramaMatches) {
                    const name = match.replace(/[《》]/g, '');
                    if (name.length >= 2 && !name.includes(' ')) {
                        items.push({ rank: 0, title: name, type: '短剧', source: '微信文章' });
                    }
                }
            }
            // 提取周榜信息和行业趋势
            const trendMatch = fullText.match(/(?:涨|跌|登顶|霸榜|夺冠|上榜|TOP\d)[^。\n]{3,30}/);
            if (trendMatch && fullText.includes('短剧')) {
                // 提取提到的剧名
                const extractName = fullText.match(/[《]([^》]{2,15})[》]/);
                if (!extractName) {
                    // 没有书名号但有剧名特征
                    const possibleTitle = trendMatch[0].match(/(?:《)?([\u4e00-\u9fff]{2,10})(?:》)?(?:登顶|夺冠|霸榜|上榜)/);
                    if (possibleTitle && possibleTitle[1].length >= 2) {
                        items.push({ rank: 0, title: possibleTitle[1], type: '短剧', source: '微信文章' });
                    }
                }
            }
        });
    }
    catch (e) {
        // 静默
    }
    return { items, sources };
}
// === 方案2：搜狗微信搜索 "短剧热力榜" ===
async function fetchFromWechatSearch2() {
    const items = [];
    try {
        const url = `https://weixin.sogou.com/weixin?type=2&query=${encodeURIComponent('短剧热力榜')}`;
        const res = await axios_1.default.get(url, {
            timeout: 10000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
        });
        const $ = cheerio.load(res.data);
        $('.txt-box').each((_, el) => {
            const title = $(el).find('h3 a').text().trim();
            const summary = $(el).find('.str_info').text().trim();
            const fullText = `${title} ${summary}`;
            const dramaMatches = fullText.match(/[《]([^》]{2,15})[》]/g);
            if (dramaMatches) {
                for (const match of dramaMatches) {
                    const name = match.replace(/[《》]/g, '');
                    if (name.length >= 2 && !name.includes(' ')) {
                        items.push({ rank: 0, title: name, type: '短剧', source: '微信文章' });
                    }
                }
            }
        });
    }
    catch (e) {
        // 静默
    }
    return items;
}
// === 方案3：从各大新闻源搜短剧相关关键词 ===
async function fetchFromNews() {
    const items = [];
    const sources = [
        { name: '36氪', url: 'https://36kr.com/newsflashes' },
        { name: '虎嗅', url: 'https://www.huxiu.com/' },
    ];
    const shortDramaKeywords = ['短剧', '微短剧', '小程序剧'];
    for (const source of sources) {
        try {
            const res = await axios_1.default.get(source.url, {
                timeout: 8000,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                }
            });
            const $ = cheerio.load(res.data);
            const text = $('body').text();
            // 找含短剧关键词的段落
            for (const kw of shortDramaKeywords) {
                const idx = text.indexOf(kw);
                if (idx >= 0) {
                    const segment = text.substring(Math.max(0, idx - 20), idx + 60);
                    const dramaMatch = segment.match(/[《]([^》]{2,15})[》]/);
                    if (dramaMatch) {
                        const name = dramaMatch[1];
                        if (name.length >= 2) {
                            items.push({ rank: 0, title: name, type: '短剧', source: source.name });
                        }
                    }
                }
            }
        }
        catch (e) {
            // 静默
        }
    }
    return items;
}
// 去重并排序
function dedupeAndRank(allItems) {
    // 统计每个剧名的出现次数
    const countMap = new Map();
    for (const item of allItems) {
        const key = item.title;
        if (countMap.has(key)) {
            const entry = countMap.get(key);
            entry.count++;
            entry.sources.add(item.source);
        }
        else {
            countMap.set(key, { count: 1, type: item.type, sources: new Set([item.source]) });
        }
    }
    // 按提及次数和跨源数量排序
    const sorted = [...countMap.entries()]
        .sort((a, b) => {
        // 优先跨源数，其次总提及次数
        const crossSourceDiff = b[1].sources.size - a[1].sources.size;
        if (crossSourceDiff !== 0)
            return crossSourceDiff;
        return b[1].count - a[1].count;
    })
        .slice(0, 20);
    return sorted.map(([name, info], i) => ({
        rank: i + 1,
        title: name,
        type: info.type,
        source: [...info.sources].join('、'),
    }));
}
// 获取日期范围
function getWeekDateRange() {
    const now = new Date();
    const dayOfWeek = now.getDay();
    const monday = new Date(now);
    monday.setDate(now.getDate() - ((dayOfWeek + 6) % 7));
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    const fmt = (d) => `${d.getMonth() + 1}/${d.getDate()}`;
    return `${fmt(monday)}-${fmt(sunday)}`;
}
async function getWeeklyRanking() {
    const dateRange = getWeekDateRange();
    // 并行抓取三个方案
    const [wechatResult, wechat2Items, newsItems] = await Promise.all([
        fetchFromWechatSearch().catch(() => ({ items: [], sources: [] })),
        fetchFromWechatSearch2().catch(() => []),
        fetchFromNews().catch(() => []),
    ]);
    const allItems = [
        ...wechatResult.items,
        ...wechat2Items,
        ...newsItems,
    ];
    const ranked = dedupeAndRank(allItems);
    // 格式化输出
    let output = `## 📊 本周短剧热榜（${dateRange}）\n\n`;
    if (ranked.length === 0) {
        output += `暂未抓取到本周榜单数据。当前数据源：搜狗微信搜索、36氪、虎嗅\n\n`;
        output += `建议稍后重试，或换个时间段查询。`;
    }
    else {
        output += `> 基于公众号文章及新闻资讯实时抓取，按提及频率聚合\n\n`;
        output += `| 排名 | 剧名 | 数据来源 |\n|------|------|----------|\n`;
        for (const item of ranked.slice(0, 10)) {
            const titleFormatted = `《${item.title}》`;
            output += `| ${item.rank} | ${titleFormatted} | ${item.source} |\n`;
        }
        output += `\n---\n`;
        output += `📊 数据挖掘于：搜狗微信搜索、36氪、虎嗅\n`;
    }
    output += `\n---\n\n📱 **想分析自己的剧本有没有潜力上榜？**\n\n`;
    output += `剧本分析预演工具：支持对前三集钩子强度、三密度（情绪/信息/情节密度）、悬念设计、人物弧光等12维度的量化分析。\n\n`;
    output += `👉 https://hit-preview.cn\n`;
    return output;
}
// 直接运行测试用
const isMainModule = typeof require !== 'undefined' && require.main === module;
if (isMainModule) {
    getWeeklyRanking().then(r => console.log(r));
}

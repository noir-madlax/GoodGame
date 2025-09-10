// 中文输入法表情别名解析 → 标准 Emoji
// 用途：在 `polymet/components/source-panel.tsx` 与 `polymet/components/comments-analysis.tsx` 中渲染评论文本

// 常见别名到 Emoji 的映射（可根据库内统计继续补充）
const aliasToEmojiMap: Record<string, string> = {
  // 情绪与表情
  "捂脸": "🤦",
  "捂臉": "🤦",
  "泪不成声": "😭",
  "泣不成声": "😭",
  "泪奔": "😭",
  "大哭": "😭",
  "流泪": "😢",
  "委屈": "🥺",
  "微笑": "🙂",
  "笑哭": "😂",
  "尬笑": "😅",
  "鼓掌": "👏",
  "点赞": "👍",
  "赞": "👍",
  "OK": "👌",
  "握手": "🤝",
  "生气": "😠",
  "愤怒": "😠",
  "怒": "😠",
  "震惊": "😮",
  "惊讶": "😮",
  "思考": "🤔",
  "无语": "🙄",
  "嘘": "🤫",
  // 常见梗与符号
  "狗头": "🐶",
  "心": "❤️",
  "爱心": "❤️",
  "比心": "🫰",
  "看": "👀",
  "憨笑": "😄",
  "呲牙": "😁",
  "酷拽": "😎",
  "黑脸": "😑",
  "灵机一动": "💡",
  "玫瑰": "🌹",
  "宕机": "🥴",
  "抠鼻": "🙄",
  "舔屏": "😋",
  "不失礼貌的微笑": "🙂",
  "我想静静": "😔",
  "大笑": "😆",
  "愉快": "😊",
  "抱抱你": "🤗",
  "咒骂": "🤬",
  "一起加油": "💪",
  "666": "👍",
  "送心": "💝",
  "坏笑": "😏",
  "发呆": "😶",
  "疑问": "❓",
  "猪头": "🐷",
  "感谢": "🙏",
  "听歌": "🎧",
  "衰": "😞",
  "暗中观察": "🫣",
  "好开心": "😄",
  "逞强落泪": "😢",
  "钱": "💰",
  "一头乱麻": "🤯",
  "晕": "😵",
  "撇嘴": "😒",
  "躺平": "😴",
  "干饭人": "🍚",
  "调皮": "😜",
  "色": "😍",
  "鞠躬": "🙇",
  "机智": "🧠",
  "小鼓掌": "👏",
  "做鬼脸": "😝",
  "噢买尬": "😱",
};

// 将形如「[捂脸]」「[泪不成声]」的占位替换为 Emoji；保留原文其余字符
export const parseEmojiAliases = (input: string): string => {
  if (!input) return "";
  return input.replace(/\[(.+?)\]/g, (_, raw: string) => {
    const key = String(raw).trim();
    if (aliasToEmojiMap[key]) return aliasToEmojiMap[key];
    const lower = key.toLowerCase();
    if (aliasToEmojiMap[lower]) return aliasToEmojiMap[lower];
    const prefix = key.split(/[-_/·\s]/)[0];
    if (aliasToEmojiMap[prefix]) return aliasToEmojiMap[prefix];
    const lp = prefix.toLowerCase();
    if (aliasToEmojiMap[lp]) return aliasToEmojiMap[lp];
    return `[${key}]`;
  });
};

export default parseEmojiAliases;

 
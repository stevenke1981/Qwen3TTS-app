"""Reusable text templates for TTS synthesis."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_TEMPLATES: list[dict] = [
    # ── 播報 (8) ────────────────────────────────────────────────
    {
        "name": "新聞播報",
        "text": "各位觀眾朋友大家好，以下是今天的重要新聞。本日頭條：多國領袖召開氣候峰會，討論全球暖化對策。",
        "category": "播報",
    },
    {
        "name": "天氣預報",
        "text": "今天天氣晴朗，氣溫介於攝氏二十五度至三十度之間，風力較弱，適合外出活動。明日起有降雨機率，請攜帶雨具。",
        "category": "播報",
    },
    {
        "name": "晨間新聞",
        "text": "早安，歡迎收聽今日晨間新聞。我是主播陳明。以下為今日重點新聞摘要：",
        "category": "播報",
    },
    {
        "name": "體育快報",
        "text": "昨日賽事精彩紛呈。世界盃足球賽八強戰，巴西以三比一擊敗阿根廷，晉級四強。",
        "category": "播報",
    },
    {
        "name": "財經播報",
        "text": "今日股市開盤，加權指數微幅上揚零點三個百分點，科技類股表現亮眼，市場情緒趨於樂觀。",
        "category": "播報",
    },
    {
        "name": "娛樂新聞",
        "text": "最新娛樂資訊，帶您了解影視圈動態。知名導演新作今日正式宣布開拍，多位一線演員確認加盟。",
        "category": "播報",
    },
    {
        "name": "科技新聞",
        "text": "科技快報：人工智慧新突破，最新語言模型在多項基準測試中刷新紀錄，引發業界廣泛關注。",
        "category": "播報",
    },
    {
        "name": "國際新聞",
        "text": "以下是今日國際新聞重點。聯合國安理會就中東局勢召開緊急會議，呼籲各方立即停火。",
        "category": "播報",
    },
    # ── 商業 (8) ────────────────────────────────────────────────
    {
        "name": "產品介紹",
        "text": "這款產品結合最先進的技術與精緻的設計，為使用者提供卓越的體驗。無論您是專業人士還是日常使用者，都能從中獲得最大的價值。",
        "category": "商業",
    },
    {
        "name": "企業簡介",
        "text": "本公司成立於二零一零年，專注於創新科技解決方案。多年來，我們服務超過五千家企業客戶，持續以品質與誠信贏得市場信任。",
        "category": "商業",
    },
    {
        "name": "會議開場",
        "text": "感謝各位撥冗出席本次會議。今天我們將針對第三季度的業績回顧及第四季度的策略規劃進行深入討論，請大家暢所欲言。",
        "category": "商業",
    },
    {
        "name": "銷售話術",
        "text": "您好，非常感謝您對我們產品的興趣！這款旗艦產品目前正在限時優惠中，多項功能已獲得業界好評，非常適合您的需求。",
        "category": "商業",
    },
    {
        "name": "品牌故事",
        "text": "我們的品牌誕生於一個簡單的信念：讓生活更美好。從一間小小的工作室出發，憑著對品質的堅持，我們成長為今日備受肯定的品牌。",
        "category": "商業",
    },
    {
        "name": "投資人簡報",
        "text": "本季度財報顯示，公司營收較去年同期增長百分之二十八，客戶留存率達九成三，持續展現強勁的成長動能。",
        "category": "商業",
    },
    {
        "name": "員工訓練",
        "text": "歡迎加入我們的大家庭！今天的新進人員訓練將涵蓋公司文化、作業流程及安全規範三大部分，請大家認真參與。",
        "category": "商業",
    },
    {
        "name": "合作提案",
        "text": "感謝貴公司對本提案的關注。我們相信此次合作能為雙方帶來雙贏的效益，以下是合作的主要條款與預期成果說明。",
        "category": "商業",
    },
    # ── 教育 (7) ────────────────────────────────────────────────
    {
        "name": "課程介紹",
        "text": "歡迎來到本課程——人工智慧基礎入門。在接下來的十二堂課中，我們將從零開始，帶您全面了解機器學習的核心概念。",
        "category": "教育",
    },
    {
        "name": "考試提醒",
        "text": "同學們請注意，下週三將舉行期中考試，考試範圍為第一章至第六章。請大家提早準備，如有疑問歡迎課後詢問。",
        "category": "教育",
    },
    {
        "name": "知識講解",
        "text": "今天我們要學習的是光合作用的基本原理。植物利用陽光、水分和二氧化碳，在葉綠體中合成葡萄糖並釋放氧氣。",
        "category": "教育",
    },
    {
        "name": "語言學習",
        "text": "Let's practice English pronunciation today. Please repeat after me: The quick brown fox jumps over the lazy dog.",
        "category": "教育",
    },
    {
        "name": "兒童故事",
        "text": "很久很久以前，在一片美麗的森林裡，住著一隻小兔子。牠每天跳來跳去，和小鳥、小松鼠做朋友，過著快樂的生活。",
        "category": "教育",
    },
    {
        "name": "科學實驗",
        "text": "今天我們要進行一個有趣的化學實驗：觀察小蘇打與醋酸的反應。請大家先將材料準備好，並注意安全規範。",
        "category": "教育",
    },
    {
        "name": "歷史課程",
        "text": "一八四零年，鴉片戰爭爆發，標誌著中國近代史的開始。這場戰爭深刻改變了中國的政治格局與社會結構。",
        "category": "教育",
    },
    # ── 故事朗讀 (7) ─────────────────────────────────────────────
    {
        "name": "有聲書段落",
        "text": "在那個寧靜的下午，她走進了那間充滿書香的小店。陽光斜斜地照進來，讓每一本書都散發著溫柔的光芒。",
        "category": "故事朗讀",
    },
    {
        "name": "詩詞朗誦",
        "text": "床前明月光，疑是地上霜。舉頭望明月，低頭思故鄉。這首李白的靜夜思，道盡了遊子思念家鄉的深情。",
        "category": "故事朗讀",
    },
    {
        "name": "散文朗讀",
        "text": "朱自清筆下的荷塘，在月色中輕輕搖曳，散發著淡淡的荷香。那是一種寧靜而悠遠的美，讓人心曠神怡。",
        "category": "故事朗讀",
    },
    {
        "name": "小說摘錄",
        "text": "那是最好的時代，也是最壞的時代；那是智慧的年代，也是愚蠢的年代；那是信仰的時期，也是懷疑的時期。",
        "category": "故事朗讀",
    },
    {
        "name": "童話故事",
        "text": "美麗的公主住在高塔之上，每天仰望著遠方的天空。她相信，某一天，勇敢的騎士會穿越迷霧森林，來到她的身邊。",
        "category": "故事朗讀",
    },
    {
        "name": "劇本旁白",
        "text": "燈光漸暗，舞台中央，一位老人正凝視著手中泛黃的信件。沉默中，歲月的重量彷彿化為空氣中的一聲嘆息。",
        "category": "故事朗讀",
    },
    {
        "name": "神話傳說",
        "text": "傳說在天地洪荒之初，盤古以一柄巨斧開天辟地。清者上升為天，濁者下沉為地，宇宙萬物，由此而生。",
        "category": "故事朗讀",
    },
    # ── 廣告行銷 (6) ─────────────────────────────────────────────
    {
        "name": "促銷廣告",
        "text": "限時特賣！全場商品最高七折優惠，活動僅限今日。數量有限，欲購從速，別讓荷包哭泣！",
        "category": "廣告行銷",
    },
    {
        "name": "品牌廣告",
        "text": "用心製造每一件商品，這是我們給您的承諾。二十年如一日，堅持品質，只為讓您的每一天都更美好。",
        "category": "廣告行銷",
    },
    {
        "name": "活動宣傳",
        "text": "盛大開幕！本週六下午兩點，誠摯邀請您蒞臨我們的旗艦店開幕典禮，現場精彩表演與豐富好禮等您來。",
        "category": "廣告行銷",
    },
    {
        "name": "網路廣告",
        "text": "點擊下方連結，立即獲取限量優惠券！加入我們的會員，獨享九折優惠與專屬新品優先購買資格。",
        "category": "廣告行銷",
    },
    {
        "name": "電視廣告",
        "text": "新一代智慧型手機，突破極限，重新定義可能。超薄機身，旗艦相機，全天候續航——夢想，就在掌心。",
        "category": "廣告行銷",
    },
    {
        "name": "廣播廣告",
        "text": "親愛的聽眾朋友，您是否有過睡眠不好、精神不濟的困擾？全新深睡寶，天然萃取，讓您一夜好眠，精力充沛。",
        "category": "廣告行銷",
    },
    # ── 客服 (6) ─────────────────────────────────────────────────
    {
        "name": "客服歡迎語",
        "text": "您好，歡迎致電客服中心！我是客服專員小明，請問今天有什麼可以為您服務的？",
        "category": "客服",
    },
    {
        "name": "等待提示",
        "text": "您好，目前客服人員正忙線中，預計等候時間約三至五分鐘。感謝您的耐心等待，我們將盡速為您服務。",
        "category": "客服",
    },
    {
        "name": "問題確認",
        "text": "感謝您的說明。根據您描述的情況，我建議您先嘗試重新啟動設備。若問題仍未解決，我們將為您安排進一步的技術支援。",
        "category": "客服",
    },
    {
        "name": "投訴處理",
        "text": "非常抱歉給您帶來不便，您的意見對我們非常重要。我們將在二十四小時內完成調查並給您回覆，敬請見諒。",
        "category": "客服",
    },
    {
        "name": "客服結束語",
        "text": "感謝您今日聯繫我們的客服中心！如您日後還有任何問題，歡迎隨時與我們聯繫。祝您有愉快的一天！",
        "category": "客服",
    },
    {
        "name": "自動應答",
        "text": "您好，本服務熱線服務時間為工作日上午九點至下午六點。如需緊急協助，請按一，查詢訂單狀態請按二。",
        "category": "客服",
    },
    # ── 社群媒體 (5) ─────────────────────────────────────────────
    {
        "name": "頻道開場白",
        "text": "大家好！我是你們的老朋友小宇，歡迎回到我的頻道！今天要跟大家分享一個超實用的生活小技巧，一定要看到最後喔！",
        "category": "社群媒體",
    },
    {
        "name": "Podcast開場",
        "text": "歡迎收聽《科技漫談》Podcast！我是您的主持人阿傑。今天我們要聊的話題是：人工智慧如何改變我們的工作模式。",
        "category": "社群媒體",
    },
    {
        "name": "影片結尾",
        "text": "好了，今天的影片就到這裡！如果您覺得有幫助的話，請記得按讚、訂閱並開啟小鈴鐺通知，我們下支影片見！",
        "category": "社群媒體",
    },
    {
        "name": "直播開場",
        "text": "直播開始囉！今天我們要帶大家進行一場精彩的開箱直播，快把朋友一起叫來看，有問題可以在留言區告訴我！",
        "category": "社群媒體",
    },
    {
        "name": "短影音旁白",
        "text": "你知道嗎？這個驚人的小技巧可以讓你的工作效率提升三倍！操作超簡單，三十秒教會你，趕快學起來！",
        "category": "社群媒體",
    },
    # ── 提醒公告 (5) ─────────────────────────────────────────────
    {
        "name": "會議通知",
        "text": "敬請注意，本週五下午三點將召開部門例會，地點為三樓會議室。請各同仁確認行程後回覆確認，謝謝配合。",
        "category": "提醒公告",
    },
    {
        "name": "活動提醒",
        "text": "提醒您，您報名的「設計思考工作坊」將於明日上午十點開始，請提前十五分鐘抵達，並攜帶個人筆記本。",
        "category": "提醒公告",
    },
    {
        "name": "系統維護公告",
        "text": "系統維護通知：本平台將於今晚十二點至明日凌晨兩點進行系統升級維護，期間服務暫停，不便之處敬請見諒。",
        "category": "提醒公告",
    },
    {
        "name": "緊急通知",
        "text": "重要緊急通知：由於颱風警報發布，明日公司宣布放颱風假，相關業務請提前安排，具體復工時間另行通知。",
        "category": "提醒公告",
    },
    {
        "name": "節日祝福",
        "text": "親愛的朋友，歲末年初，值此新春佳節，謹祝您新年快樂、身體健康、萬事如意、闔家幸福！",
        "category": "提醒公告",
    },
    # ── 娛樂 (4) ─────────────────────────────────────────────────
    {
        "name": "遊戲旁白",
        "text": "冒險已然開始。英雄將踏入黑暗王國，面對前所未有的挑戰。命運的齒輪開始轉動，一切，將由您來決定。",
        "category": "娛樂",
    },
    {
        "name": "電影預告",
        "text": "今年最令人期待的科幻大片，即將震撼登場。當文明的邊界被打破，人類最後的希望，只剩下這一個選擇。",
        "category": "娛樂",
    },
    {
        "name": "音樂節目介紹",
        "text": "接下來，請欣賞由鋼琴家王立群所演奏的蕭邦夜曲，在這個寧靜的夜晚，讓音樂帶您進入另一個世界。",
        "category": "娛樂",
    },
    {
        "name": "節目預告",
        "text": "精彩節目即將播出！今晚八點，超人氣綜藝節目《歡樂全家人》帶來全新一季，笑聲與感動，一個都不少！",
        "category": "娛樂",
    },
]


@dataclass
class TextTemplate:
    name: str
    text: str
    category: str = "自訂"


@dataclass
class TemplateStore:
    """Manage user text templates on disk (JSON)."""

    templates: list[TextTemplate] = field(default_factory=list)
    _path: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, path: Path) -> TemplateStore:
        store = cls(_path=path)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                store.templates = [TextTemplate(**item) for item in raw]
            except Exception:
                log.warning("無法讀取模板檔案 %s，使用預設模板", path)
                store.templates = [TextTemplate(**d) for d in _DEFAULT_TEMPLATES]
        else:
            store.templates = [TextTemplate(**d) for d in _DEFAULT_TEMPLATES]
            store.save()
        return store

    def save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(t) for t in self.templates]
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, name: str, text: str, category: str = "自訂") -> TextTemplate:
        tpl = TextTemplate(name=name, text=text, category=category)
        self.templates.append(tpl)
        self.save()
        return tpl

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.templates):
            self.templates.pop(index)
            self.save()

    def categories(self) -> list[str]:
        return sorted({t.category for t in self.templates})

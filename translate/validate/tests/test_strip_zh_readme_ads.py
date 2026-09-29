"""strip_zh_readme_ads removes upstream ad and reward blocks."""

from forge.ops.strip_zh_readme_ads import strip_ads


def test_strips_reward_qr_and_keeps_license():
    text = (
        "## 许可\n\nCC BY\n\n## Star 走势\n\nchart\n\n## 赞赏\n\n"
        '<img src="ads/wechat-reward.png" alt="微信赞赏码" width="240">\n'
    )
    cleaned = strip_ads(text)
    assert "## 赞赏" not in cleaned
    assert "ads/wechat-reward.png" not in cleaned
    assert "## 许可" in cleaned
    assert "## Star 走势" in cleaned


def test_strips_ad_slot():
    text = "## 许可\n\nbody\n\n## 广告位\n\n[ad](ads/mcyyy.webp)\n"
    cleaned = strip_ads(text)
    assert "## 广告位" not in cleaned
    assert "ads/" not in cleaned
    assert "## 许可" in cleaned

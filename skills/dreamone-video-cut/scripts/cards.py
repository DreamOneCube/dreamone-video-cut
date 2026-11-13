"""資訊卡 PNG：深色半透明圓角底、可選的編號圓章、標題、內文行（可帶打勾）。"""
from PIL import Image, ImageDraw, ImageFont

BG = (14, 17, 22, 225)
YELLOW = (255, 212, 0, 255)
WHITE = (255, 255, 255, 255)
GREY = (200, 205, 212, 255)


def card(font_path, out, width, title, num=None, lines=(), checks=False):
    """lines: 內文字串；checks=True 時每行前面畫黃色勾。"""
    S = 2  # 2 倍繪製再縮小，邊緣較平滑
    ft = ImageFont.truetype(font_path, 46 * S)
    fl = ImageFont.truetype(font_path, 36 * S)
    pad, gap, badge = 22 * S, 6 * S, 60 * S
    lh, th = 46 * S, 56 * S
    h = pad * 2 + th + (gap + lh * len(lines) if lines else 0)
    w = width * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28 * S, fill=BG)
    d.rounded_rectangle([0, 0, 10 * S, h - 1], radius=5 * S, fill=YELLOW)
    x, y = pad + 6 * S, pad
    if num:
        d.ellipse([x, y + (th - badge) / 2, x + badge, y + (th + badge) / 2], fill=YELLOW)
        d.text((x + badge / 2, y + th / 2), str(num), font=ft, fill=(14, 17, 22, 255), anchor="mm")
        x += badge + 18 * S
    d.text((x, y + th / 2), title, font=ft, fill=YELLOW if not num else WHITE, anchor="lm")
    y += th + gap
    for ln in lines:
        lx = pad + 6 * S
        if checks:
            cy = y + lh / 2
            d.line([(lx + 4 * S, cy), (lx + 14 * S, cy + 11 * S), (lx + 32 * S, cy - 12 * S)],
                   fill=YELLOW, width=7 * S, joint="curve")
            lx += 46 * S
        d.text((lx, y + lh / 2), ln, font=fl, fill=GREY if not checks else WHITE, anchor="lm")
        y += lh
    im.resize((w // S, h // S), Image.LANCZOS).save(out)
    return w // S, h // S


def label(font_path, out, text, sub):
    """B-roll 上方的來源標籤。"""
    S = 2
    ft, fs = ImageFont.truetype(font_path, 44 * S), ImageFont.truetype(font_path, 28 * S)
    w = int(max(ft.getlength(text), fs.getlength(sub))) + 60 * S
    h = 118 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=20 * S, fill=BG)
    d.text((30 * S, 38 * S), text, font=ft, fill=WHITE, anchor="lm")
    d.text((30 * S, 88 * S), sub, font=fs, fill=GREY, anchor="lm")
    im.resize((w // S, h // S), Image.LANCZOS).save(out)
    return w // S, h // S


def tag(font_path, out, text):
    """B-roll 畫面上的小標籤（例：隊伍名稱）。"""
    S = 2
    f = ImageFont.truetype(font_path, 36 * S)
    w, h = int(f.getlength(text)) + 36 * S, 58 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=14 * S, fill=YELLOW)
    d.text((w / 2, h / 2), text, font=f, fill=(14, 17, 22, 255), anchor="mm")
    im.resize((w // S, h // S), Image.LANCZOS).save(out)
    return w // S, h // S


def panel_card(src, box, out, width=980, pad=18, radius=36):
    """從資訊圖（例：課程介紹圖）裁出一塊，放大到 width，加同色圓角底與陰影，當影片裡的卡片。
    box=(左, 上, 右, 下)，像素座標；底色取原圖左上角。"""
    from PIL import ImageFilter
    im = Image.open(src).convert("RGBA")
    bg = im.getpixel((5, 5))
    c = im.crop(box)
    c = c.resize((width, int(c.height * width / c.width)), Image.LANCZOS)
    w, h = c.width + 2 * pad, c.height + 2 * pad
    card = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([20, 28, 20 + w, 28 + h], radius, fill=(0, 0, 0, 120))
    card.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    face = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(face).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=bg)
    face.alpha_composite(c, (pad, pad))
    card.alpha_composite(face, (20, 20))
    card.save(out)
    return card.size

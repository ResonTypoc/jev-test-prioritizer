# 名前の前後の空白を取り除き、挨拶文を返すサンプル。
class Formatter
  # 公開メソッドとして、整形した名前を挨拶文に埋め込む。
  def format(name)
    "Hello, #{normalize(name)}!"
  end

  private

  # 名前の前後の空白だけを取り除く内部処理。
  def normalize(name)
    name.strip
  end
end

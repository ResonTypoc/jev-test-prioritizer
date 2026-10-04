require "minitest/autorun"
require_relative "formatter"

class FormatterTest < Minitest::Test
  # 実装詳細に依存するテストの例。send で非公開メソッドを直接呼び出し、
  # もともと前後に空白がない文字列が変わらないことだけを確認する。
  # 公開メソッド format の挨拶文や、前後の空白が除去されることは検証していない。
  def test_private_helper_preserves_an_already_clean_string
    assert_equal "Ada", Formatter.new.send(:normalize, "Ada")
  end
end

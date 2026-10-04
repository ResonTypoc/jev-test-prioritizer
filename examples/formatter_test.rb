require "minitest/autorun"
require_relative "formatter"

class FormatterTest < Minitest::Test
  def test_private_helper_preserves_an_already_clean_string
    assert_equal "Ada", Formatter.new.send(:normalize, "Ada")
  end
end

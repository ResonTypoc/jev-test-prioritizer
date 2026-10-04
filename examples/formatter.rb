class Formatter
  def format(name)
    "Hello, #{normalize(name)}!"
  end

  private

  def normalize(name)
    name.strip
  end
end

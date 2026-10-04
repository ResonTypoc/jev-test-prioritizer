# 無効な金額を決済ゲートウェイへ渡さないためのサンプル。
class PaymentService
  # 実際の決済処理を担当するゲートウェイを外部から受け取る。
  def initialize(gateway)
    @gateway = gateway
  end

  def charge(amount)
    # 0以下の金額は、ゲートウェイを呼び出す前に例外で拒否する。
    raise ArgumentError, "amount must be positive" unless amount.positive?

    # 正の金額はゲートウェイへ渡し、その戻り値を返す。
    @gateway.charge(amount)
  end
end

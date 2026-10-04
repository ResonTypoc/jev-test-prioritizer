require "minitest/autorun"
require_relative "payment_service"

class PaymentServiceTest < Minitest::Test
  # 無効な金額が拒否され、決済ゲートウェイに到達しないという振る舞いを検証する。
  def test_rejects_nonpositive_payments_before_charging
    # ゲートウェイの代役。呼び出されたら失敗させ、無効な決済の到達を検出する。
    gateway = Object.new
    def gateway.charge(_amount)
      raise "an invalid payment reached the gateway"
    end

    service = PaymentService.new(gateway)
    # 境界値の0と負数を試し、どちらも ArgumentError で拒否されることを確認する。
    [0, -1].each do |amount|
      error = assert_raises(ArgumentError) { service.charge(amount) }
      # 例外メッセージも完全一致で確認するため、その文言には依存している。
      assert_equal "amount must be positive", error.message
    end
  end
end

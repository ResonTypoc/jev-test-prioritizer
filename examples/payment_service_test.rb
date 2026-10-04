require "minitest/autorun"
require_relative "payment_service"

class PaymentServiceTest < Minitest::Test
  def test_rejects_nonpositive_payments_before_charging
    gateway = Object.new
    def gateway.charge(_amount)
      raise "an invalid payment reached the gateway"
    end

    service = PaymentService.new(gateway)
    [0, -1].each do |amount|
      error = assert_raises(ArgumentError) { service.charge(amount) }
      assert_equal "amount must be positive", error.message
    end
  end
end

class PaymentService
  def initialize(gateway)
    @gateway = gateway
  end

  def charge(amount)
    raise ArgumentError, "amount must be positive" unless amount.positive?

    @gateway.charge(amount)
  end
end

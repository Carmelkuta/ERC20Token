// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import '../interfaces/IERC20.sol';
import '../interfaces/IExchange.sol';

contract RUExchange is IExchange {

    //The token on the exchange
    IERC20 private ruToken;

    //fee percentage
    uint private fee;

    //initial supply of tokens
    uint private tokSupply;

    //initial ETH supply
    uint private ETHSupply;

    //Owner of the AMM exchange
    address private AMMowner;

    //The constant to be maintained
    uint private k;

    //Dictionary of Liquidity-token balances
    mapping(address => uint256) public _balances;

    //Number of LQTs
    uint private LQTokens;

    //Dictionary of allowances
    mapping(address => mapping(address => uint256)) public _allowances;


    //Owner of the AMM exchange
    constructor() {
        AMMowner = msg.sender;
    }

    function initialize(IERC20 _RUXtoken, uint8 _feePercent, uint initialTOK, uint initialETH) override public payable returns(uint) {
        // TODO: Implement
        require(AMMowner == msg.sender);
        ruToken = _RUXtoken;
        require(ruToken.allowance(AMMowner, address(this)) >= initialTOK);
        require(ruToken.transferFrom(AMMowner, address(this), initialTOK));
        fee = _feePercent;
        k = initialETH * initialTOK;
        tokSupply = initialTOK;
        ETHSupply = initialETH;
        _balances[msg.sender] = initialTOK;
        LQTokens = initialTOK;
    }

    /**
     * Returns the current number of tokens in the liquidity pool.
     */
    function tokenBalance() external view returns(uint) {
        // TODO: Implement
        return tokSupply;
    }

    /**
     * Calculate the fees so that it rounds up.
     */
    function calculateFee(uint amount) view private returns(uint) {
        uint calculatedFee = 0;
        if ((amount * fee) % 100 == 0) {
            calculatedFee = ((amount * fee) / 100);
        }
        else {
            calculatedFee = ((amount * fee) / 100) + 1;
        }
        return calculatedFee;
    }
    

   /**
     * @dev Swap ETH for tokens.
     * Buy `amount` tokens as long as the total price is at most `maxPrice`. revert if this is impossible.
     * Note that the fee is taken in *both* tokens and ETH. The fee percentage is taken from `amount` tokens 
     * (rounded up) *after* they are bought, and taken from the ETH sent (rounded up) *before* the purchase.
     * @return Returns the actual total cost in ETH including fee.
     */
    function buyTokens(uint amount, uint maxPrice) override public payable returns (uint,uint,uint) {
        // TODO: Implement

        //exchange first takes fee in eth
        uint offerPrice = (k/(tokSupply - amount)) - ETHSupply;
        uint ETHFee = calculateFee(offerPrice);
        uint totalPrice = offerPrice+ETHFee;
        require(totalPrice <= maxPrice);


        uint tokenFee = calculateFee(amount);
        uint tokensToSell = amount - tokenFee;
        require(tokensToSell <= tokSupply);

        //transfer them tokens
        require(ruToken.transfer(msg.sender, tokensToSell));

        //transfer back any extra ETH retained from the transaction
        uint retainedETH = maxPrice - totalPrice;
        if (retainedETH > 0) {
        address payable receiver = payable(msg.sender);
        receiver.transfer(retainedETH);
        }

        tokSupply -= tokensToSell;
        ETHSupply += totalPrice;
        k = tokSupply * ETHSupply;

        return (totalPrice, ETHFee+ETHFee, tokenFee);
    }

    /**
     * @dev Swap tokens for ETH
     * Sell `amount` tokens as long as the total price is at least `minPrice`. revert if this is impossible.
     * Note that the fee is taken in *both* tokens and ETH. The fee percentage is taken from `amount` tokens 
     * (rounded up) *before* selling, and taken from the ETH returned (rounded up) *after* selling.
     * @return Returns a tuple with the actual total value in ETH minus the fee, the eth fee and the token fee.
     */
    function sellTokens(uint amount, uint minPrice) override public returns (uint, uint, uint) {
        // TODO: Implement

        uint tokenFee = calculateFee(amount);      
        uint tokensToBuy = amount - tokenFee;
        uint rawPrice = ETHSupply - (k / (tokSupply + tokensToBuy)); //May switch token Fee with TokensToBuy if error exists
        uint ETHFee = calculateFee(rawPrice);

        
        uint offerPrice = rawPrice - ETHFee;
        require(offerPrice <= ETHSupply);
        require(offerPrice >= minPrice);

        //TODO: send amount of tokens to contract, send amount of ETH to sender. Round up 

        ruToken.transferFrom(msg.sender, address(this), amount);
        address payable receiver = payable(msg.sender);
        receiver.transfer(offerPrice);

        tokSupply += amount;
        ETHSupply -= offerPrice;
        k = tokSupply * ETHSupply;

        return (offerPrice, ETHFee, tokenFee);
    }

    /**
     * @dev mint `amount` liquidity tokens, as long as the total number of tokens spent is at most `maxTOK`
     * and the total amount of ETH spent is `maxETH`. The token allowance for the exchange address must be at least `maxTOK`,
     * and the msg value at least `maxETH`.
     * Unused funds will be returned to the sender.
     * @return returns a tuple consisting of (token_spent, eth_spent). 
     */
    function mintLiquidityTokens(uint amount, uint maxTOK, uint maxETH) public payable returns (uint,uint) {
        // TODO: Implement
        uint tokUnit = tokSupply / LQTokens ;

        uint ethNeeded = (ETHSupply * amount) / LQTokens;
        uint tokNeeded = tokUnit * amount;

        require(ethNeeded <= maxETH && tokNeeded <= maxTOK);
        require(ruToken.allowance(msg.sender, address(this)) >= maxTOK);
        require(msg.value >= maxETH);

        require(ruToken.transferFrom(msg.sender, address(this), tokNeeded));
        address payable receiver = payable(msg.sender);
        receiver.transfer(msg.value - ethNeeded);

        if (_balances[msg.sender] > 0){
            _balances[msg.sender] += amount;
        } else {
            _balances[msg.sender] = amount;
        }

        LQTokens += amount;
        tokSupply += tokNeeded;
        ETHSupply += ethNeeded;
        k = tokSupply*ETHSupply;

        return (tokNeeded, ethNeeded);


    }

    /**
     * @dev burn `amount` liquidity tokens, as long as this will result in at least minTOK tokens and at least minETH eth being generated.
     * The resulting tokens and ETH will be credited to the sender.
     * @return Returns a tuple consisting of (token_credited, eth_credited). 
     */
    function burnLiquidityTokens(uint amount, uint minTOK, uint minETH) override public payable returns (uint,uint) {
        // TODO: Implement
        uint tokUnit = tokSupply / LQTokens;

        uint ethGiven = (ETHSupply * amount) / LQTokens;
        uint tokGiven = tokUnit * amount;

        require(ethGiven >= minETH && tokGiven >= minTOK);
        require(_balances[msg.sender] >= amount);
        require(ETHSupply >= ethGiven && tokSupply >= tokGiven);

        ruToken.transfer(msg.sender, tokGiven);
        address payable receiver = payable(msg.sender);
        receiver.transfer(ethGiven);

        _balances[msg.sender] -= amount;
        LQTokens -= amount;
        tokSupply -= tokGiven;
        ETHSupply -= ethGiven;
        k = tokSupply*ETHSupply;

        return (tokGiven, ethGiven);

    }

    /**
     * @dev Returns the amount of tokens in existence.
     */
    function totalSupply() external view returns (uint256) {
        // TODO: Implement
        return LQTokens;
    }

    /**
     * @dev Returns the amount of tokens owned by `account`.
     */
    function balanceOf(address account) public view override returns (uint256) {
        // TODO: Implement
        return _balances[account];
    }


    /**
     * @dev Moves `amount` tokens from the caller's account to `recipient`.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address recipient, uint256 amount) external override returns (bool) {
        // TODO: Implement
        require(recipient != address(0) && msg.sender != address(0));
        require(_balances[msg.sender] >= amount && amount >= 0);
        _balances[msg.sender] -= amount;
        _balances[recipient] += amount;
        
        emit Transfer(msg.sender, recipient, amount);
        return true;
    }

    /**
     * @dev Returns the remaining number of tokens that `spender` will be
     * allowed to spend on behalf of `owner` through {transferFrom}. This is
     * zero by default.
     *
     * This value changes when {approve} or {transferFrom} are called.
     */
    function allowance(address owner, address spender) external view override returns (uint256) {
        // TODO: Implement
        return _allowances[owner][spender];
    }

    /**
     * @dev Sets `amount` as the allowance of `spender` over the caller's tokens.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * IMPORTANT: Beware that changing an allowance with this method brings the risk
     * that someone may use both the old and the new allowance by unfortunate
     * transaction ordering. One possible solution to mitigate this race
     * condition is to first reduce the spender's allowance to 0 and set the
     * desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     *
     * Emits an {Approval} event.
     */
    function approve(address spender, uint256 amount) external override returns (bool) {
        // TODO: Implement
        require(amount >= 0);
        _allowances[msg.sender][spender] = 0;
        emit Approval(msg.sender, spender, amount);
        _allowances[msg.sender][spender] = amount;

        return true;
    }

    /**
     * @dev Moves `amount` tokens from `sender` to `recipient` using the
     * allowance mechanism. `amount` is then deducted from the caller's
     * allowance.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transferFrom(address sender, address recipient, uint256 amount) external override returns (bool) {
        // TODO: Implement
        require(_balances[sender] >= amount && amount >= 0 && _allowances[sender][msg.sender] >= amount);
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        _allowances[sender][msg.sender] -= amount;
        emit Transfer(sender, recipient, amount);
        return true;
    }
}
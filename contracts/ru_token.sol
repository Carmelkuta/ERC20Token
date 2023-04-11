// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../interfaces/IERC20.sol";
import "../interfaces/IMultisigToken.sol";


/**
 * @dev An implementation of the ERC20 standard for a "Reichman University" Token.
 */
contract RUToken is IERC20, IERC20Metadata {
    /**
     * Maximum number of mintable tokens.
     */
    uint public maxTokens;

    /**
     * Price required to mint a token in ETH
     */
    uint public tokenPrice;

    

    //Dictionary of balances
    mapping(address => uint256) public _balances;

    //Dictionary of allowances
    mapping(address => mapping(address => uint256)) public _allowances;

    //Create a total number of tokens being circulated
    uint256 public total_supply = 0;


    constructor(uint _tokenPrice, uint _maxTokens) {
        tokenPrice = _tokenPrice;
        maxTokens = _maxTokens;
    }

    /**
    * @dev Returns the decimals places of the token.
    */
    function decimals() external pure override returns (uint8) {
        return 18;
    }

    function name() public pure override returns (string memory) {
        return "Reichman U Token";
    }

    function symbol() public pure override returns (string memory) {
        return "RUX";
    }


    /**
     * @dev Returns the amount of tokens in existence.
     */
    function totalSupply() external view returns (uint256) {
        // TODO: Implement
        return total_supply;
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

    /**
     * @dev Mint a new token. 
     * The total number of tokens minted is the msg value divided by tokenPrice.
     */
    function mint() public payable returns (uint) {
        // TODO: Implement
        require(msg.sender != address(0));
        require(msg.value > 0);
        uint numTokens = (msg.value / tokenPrice);
        require(numTokens + total_supply <= maxTokens);
        if (_balances[msg.sender] > 0){
        _balances[msg.sender] += numTokens;
        } else {
        _balances[msg.sender] = numTokens;
        }
        total_supply += numTokens;
        return numTokens;
    }

    /**
     * Burn `amount` tokens. The corresponding value (`tokenPrice` for each token) is sent to the caller.
     */
    function burn(uint amount) public {
        // TODO: Implement
        require(msg.sender != address(0));
        require(_balances[msg.sender] >= amount && amount > 0);
        _balances[msg.sender] -= amount;
        _balances[address(0)] += amount;
        address payable receiver = payable(msg.sender);
        receiver.transfer(amount*tokenPrice);
        total_supply -= amount;
    }
}
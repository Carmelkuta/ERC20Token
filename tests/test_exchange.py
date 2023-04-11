from math import ceil
import pytest
import brownie

from brownie import RUExchange, RUToken, accounts
from brownie.test import given, strategy
from hypothesis import settings
from hypothesis.strategies import tuples
from tests.test_tokens import msg, deploy_ru_token, mint_ru_tokens, checkFailedTransfer, checkSuccessfulTransfer, GenericTokenTest
from scripts.exchange import grade_exchange

pytestmark = pytest.mark.skipif(not grade_exchange, reason="Exchange not implemented! (Set bonus_multisig_token.grade_bonus = True to allow grading)")

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

# Globals
default_price = 100
default_xfernum = 200 
default_totalmint = default_xfernum * 4
default_maxtok = 1e15
default_feepercent = 5

default_initial_tokens = 100
default_initial_eth = 200


def deploy_ru_exchange(account) -> RUExchange:
    exch = RUExchange.deploy(msg(account))
    return exch

def initialize_ru_exchange(exch: RUExchange, tok: RUToken, account, fee: int, initial_tokens: int, initial_eth: int):
    mint_ru_tokens(tok, account, initial_tokens)
    tok.approve(exch, initial_tokens, msg(account))
    tx = exch.initialize(tok, fee, initial_tokens, initial_eth, msg(account, initial_eth))
    return tx.return_value



@pytest.fixture(autouse=True, scope='class')
def default_setup(request):
    request.cls.price = default_price
    request.cls.maxtok = default_maxtok
    request.cls.rutoken = deploy_ru_token(default_price, default_maxtok, accounts[0])
    request.cls.feePercent = default_feepercent
    request.cls.initial_tokens = default_initial_tokens
    request.cls.initial_eth = default_initial_eth


class TestExchangeSpecifics:
    def deploy_and_init_exchange(self, owner_account) -> RUExchange:
        exch = deploy_ru_exchange(owner_account)
        initialize_ru_exchange(exch, self.rutoken, owner_account, self.feePercent, self.initial_tokens, self.initial_eth)
        return exch


    def buytoken_testbody(self, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        buytokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[0])

        orig_exch_balance =  exch.balance()
        orig_exch_tokenbalance = exch.tokenBalance()
        
        orig_tokenbalance = self.rutoken.balanceOf(accounts[1])
        orig_eth_balance = accounts[1].balance()

        tx = exch.buyTokens(buytokens, 1e7, msg(accounts[1], 1e7))

        actualPayment, actualEthFee, actualTokenFee = tx.return_value


        exactEthFee = self.feePercent * (actualPayment) / 100
        exactTokenFee = buytokens * self.feePercent / 100

        assert int(exactTokenFee) <= actualTokenFee <= ceil(exactTokenFee)
        assert int(exactEthFee) <= actualEthFee <= ceil(exactEthFee)

        new_exch_balance = exch.balance()
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = self.rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance()

        assert new_tokenbalance == orig_tokenbalance + buytokens - actualTokenFee
        assert new_eth_balance == orig_eth_balance - actualPayment
        assert new_exch_tokenbalance == orig_exch_tokenbalance - buytokens + actualTokenFee
        assert new_exch_balance == orig_exch_balance + actualPayment

        orig_k = orig_exch_tokenbalance * orig_exch_balance
        new_exch_balance_without_fee = new_exch_balance - actualEthFee
        new_exch_tokenbalance_without_fee = new_exch_tokenbalance - actualTokenFee

        print(f"---------------------------------\nOrig K = TokenBalance * ETHBalance: {orig_k} = {orig_exch_tokenbalance} * {orig_exch_balance}\nNew K = newTokenBalance * NewETHBalance: {new_exch_balance*new_exch_tokenbalance} = {new_exch_tokenbalance} * {new_exch_balance}") 
        print(f"Orig K = (NewTokenBalance-TokenFee) * (NewethBalance-ethFee): {orig_k} = ({new_exch_tokenbalance}-{actualTokenFee}) * ({new_exch_balance}-{actualEthFee})")      
        print(f"TokensToBuy: {buytokens}\nTokenFee: {actualTokenFee}\n")
        print(f"ethToSell: {actualPayment}\nethFee {actualEthFee}")

        # We tolerate off-by-one errors that can occur due to rounding
        assert new_exch_tokenbalance_without_fee * (new_exch_balance_without_fee - 1) <= orig_k <= new_exch_tokenbalance_without_fee * (new_exch_balance_without_fee + 1)

    def test_simple_buy1token(self):
        self.buytoken_testbody(0, 100, (1, 100))


    @given(
        feepercent=strategy('uint', min_value=0, max_value=95),
        initial_eth=strategy('uint', min_value=10, max_value=300),
        # tokens_to_buy, initialsupply
        tokdata=tuples(strategy('uint', min_value=1, max_value=100),strategy('uint', min_value=2, max_value=100)).map(sorted).filter(lambda x: x[0] < x[1]),
    )
    @settings(max_examples=20)
    def test_buytokens(self, feepercent, initial_eth, tokdata):
        self.buytoken_testbody(feepercent, initial_eth, tokdata)



    def selltoken_testbody(self, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        sellTokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[0])

        orig_exch_balance =  exch.balance()
        orig_exch_tokenbalance = exch.tokenBalance()
        
        tokenprice = self.rutoken.tokenPrice()
        self.rutoken.mint(msg(accounts[1], sellTokens * tokenprice))

        orig_tokenbalance = self.rutoken.balanceOf(accounts[1])
        assert orig_tokenbalance >= sellTokens

        orig_eth_balance = accounts[1].balance()

        self.rutoken.approve(exch, sellTokens, msg(accounts[1]))
        tx = exch.sellTokens(sellTokens, 0, msg(accounts[1]))

        actualPayment, actualEthFee, actualTokenFee = tx.return_value
        exactEthFee = self.feePercent * (actualPayment + actualEthFee) / 100
        exactTokenFee = sellTokens * self.feePercent / 100

        assert int(exactEthFee) <= actualEthFee <= ceil(exactEthFee)
        assert int(exactTokenFee) <= actualTokenFee <= ceil(exactTokenFee)

        new_exch_balance = exch.balance()
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = self.rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance()

        assert new_eth_balance == orig_eth_balance + actualPayment
        assert new_tokenbalance == orig_tokenbalance - sellTokens
        assert new_exch_tokenbalance == orig_exch_tokenbalance + sellTokens 
        assert new_exch_balance == orig_exch_balance - actualPayment

        orig_k = orig_exch_tokenbalance * orig_exch_balance
        new_exch_balance_without_fee = new_exch_balance - actualEthFee 
        new_exch_tokenbalance_without_fee = new_exch_tokenbalance - actualTokenFee

        # We tolerate off-by-one errors that can occur due to rounding
        assert new_exch_tokenbalance_without_fee * (new_exch_balance_without_fee - 1) <= orig_k <= new_exch_tokenbalance_without_fee * (new_exch_balance_without_fee + 1)


    def test_simple_sell1token(self):
        self.selltoken_testbody(0, 10, (1, 10))


    @given(
        feepercent=strategy('uint', min_value=0, max_value=95),
        initial_eth=strategy('uint', min_value=10, max_value=300),
        # tokens_to_sell, initialsupply
        tokdata=tuples(strategy('uint', min_value=1, max_value=100),strategy('uint', min_value=1, max_value=100))
    )
    @settings(max_examples=20)
    def test_selltokens(self, feepercent, initial_eth, tokdata):
        self.selltoken_testbody(feepercent, initial_eth, tokdata)


    def mintliquidity_testbody(self, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        mintTokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[0])

        orig_exch_balance =  exch.balance()
        
        self.rutoken.mint(msg(accounts[1], 1e6))

        orig_tokenbalance = self.rutoken.balanceOf(accounts[1])
        orig_eth_balance = accounts[1].balance()
        orig_exch_tokenbalance = exch.tokenBalance()

        orig_lqt_balance = exch.balanceOf(accounts[1])

        self.rutoken.approve(exch, 1e6, msg(accounts[1]))
        tx = exch.mintLiquidityTokens(mintTokens, 1e6, 1e6, msg(accounts[1], 1e6))
        numTOK, numETH = tx.return_value

        new_exch_balance = exch.balance()
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = self.rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance()
        new_lqt_balance = exch.balanceOf(accounts[1])

        assert new_lqt_balance == orig_lqt_balance + mintTokens
        assert new_exch_balance == orig_exch_balance + numETH
        assert new_exch_tokenbalance == orig_exch_tokenbalance + numTOK
        assert new_eth_balance == orig_eth_balance - numETH
        assert new_tokenbalance == orig_tokenbalance - numTOK

        newTotalLQT = exch.totalSupply()
        lqtFraction = mintTokens / newTotalLQT

        assert int(new_exch_tokenbalance * lqtFraction) <= numTOK <= ceil(new_exch_tokenbalance * lqtFraction)
        assert int(new_exch_balance * lqtFraction) <= numETH <= ceil(new_exch_balance * lqtFraction)



    def test_simple_mint1token(self):
        self.mintliquidity_testbody(0, 10, (1, 10))

    @given(
        feepercent=strategy('uint', min_value=0, max_value=95),
        initial_eth=strategy('uint', min_value=10, max_value=300),
        # tokens_to_mint, initialsupply
        tokdata=tuples(strategy('uint', min_value=1, max_value=100),strategy('uint', min_value=1, max_value=100))
    )
    @settings(max_examples=20)
    def test_mintliquidity(self, feepercent, initial_eth, tokdata):
        self.mintliquidity_testbody(feepercent, initial_eth, tokdata)



    def burnliquidity_testbody(self, feepercent, initial_eth, tokdata):
        self.feePercent = feepercent
        self.initial_eth = initial_eth
        burnTokens, self.initial_tokens = tokdata
        exch = self.deploy_and_init_exchange(accounts[1])

        orig_exch_balance =  exch.balance()
        orig_tokenbalance = self.rutoken.balanceOf(accounts[1])
        orig_eth_balance = accounts[1].balance()
        orig_exch_tokenbalance = exch.tokenBalance()
        orig_lqt_balance = exch.balanceOf(accounts[1])

        orig_totalLQT = exch.totalSupply()
        lqtFraction = burnTokens / orig_totalLQT

        tx = exch.burnLiquidityTokens(burnTokens, 0, 0, msg(accounts[1]))
        numTOK, numETH = tx.return_value

        new_exch_balance = exch.balance()
        new_exch_tokenbalance = exch.tokenBalance()
        new_tokenbalance = self.rutoken.balanceOf(accounts[1])
        new_eth_balance = accounts[1].balance()
        new_lqt_balance = exch.balanceOf(accounts[1])

        assert new_lqt_balance == orig_lqt_balance - burnTokens
        assert new_exch_balance == orig_exch_balance - numETH
        assert new_exch_tokenbalance == orig_exch_tokenbalance - numTOK
        assert new_eth_balance == orig_eth_balance + numETH
        assert new_tokenbalance == orig_tokenbalance + numTOK

        assert int(orig_exch_tokenbalance * lqtFraction) <= numTOK <= ceil(orig_exch_tokenbalance * lqtFraction)
        assert int(orig_exch_balance * lqtFraction) <= numETH <= ceil(orig_exch_balance * lqtFraction)

    def test_simple_burn1token(self):
        self.mintliquidity_testbody(0, 10, (1, 10))

    @given(
        feepercent=strategy('uint', min_value=0, max_value=95),
        initial_eth=strategy('uint', min_value=10, max_value=300),
        # tokens_to_burn, initialsupply
        tokdata=tuples(strategy('uint', min_value=1, max_value=100),strategy('uint', min_value=2, max_value=100)).map(sorted).filter(lambda x: x[0] < x[1]),
    )
    @settings(max_examples=20)
    def test_burnliquidity(self, feepercent, initial_eth, tokdata):
        self.burnliquidity_testbody(feepercent, initial_eth, tokdata)



class TestExchangeAsToken(GenericTokenTest):
    # Must override this function!
    # Returns a token instance
    def deploy_tok(self, account):
        # newacct = accounts.add()
        exch = deploy_ru_exchange(account)
        initialize_ru_exchange(exch, self.rutoken, account, self.feePercent, self.initial_tokens, self.initial_eth)
        return exch

    # Must override this function
    # returns a transaction receipt.
    def mint_funds(self, exch: RUExchange, account, amount):
        curSupply = exch.totalSupply()
        curTok = exch.tokenBalance()
        curEth = exch.balance()

        orig_lqt_balance = exch.balanceOf(account)
        orig_rutok_balance = self.rutoken.balanceOf(account)

        mint_ru_tokens(self.rutoken, account, 1e6)
        self.rutoken.approve(exch, 1e6, msg(account))
        tx = exch.mintLiquidityTokens(amount, 1e6, 1e6, msg(account, 1e6))

        assert exch.balanceOf(account) == orig_lqt_balance + amount
        new_tokenbalance = self.rutoken.balanceOf(account)
        self.rutoken.burn(new_tokenbalance - orig_rutok_balance, msg(account))
        return tx
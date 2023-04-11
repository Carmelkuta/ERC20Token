from re import A
import pytest
import brownie
from brownie import RUToken, accounts
from brownie.test import given, strategy
from hypothesis import settings
from hypothesis.strategies import sampled_from




def msg(account, amount: int = 0) -> dict:
    if isinstance(account, int):
        account = accounts[account]

    return {'amount': amount, 'from': account}

def transfer_direct(tok, src, dst, sender, amount):
    return tok.transfer(dst, amount, msg(sender))

def transfer_byproxy(tok, src, dst, sender, amount):
    return tok.transferFrom(src, dst, amount, msg(sender))


def checkSuccessfulTransfer(tok, src, dst, sender, amount, transferFunc):
    orig_token_balance = tok.balanceOf(dst, msg(0))

    tx = transferFunc(tok, src, dst, sender, amount)

    new_token_balance = tok.balanceOf(dst, msg(0))

    if src != dst:
        assert new_token_balance == orig_token_balance + amount
    else:
        assert new_token_balance == orig_token_balance

    assert 'Transfer' in tx.events # Check that the Transfer event was produced
    assert tx.events['Transfer']['value'] == amount
    assert tx.events['Transfer']['from'] == src.address
    assert tx.events['Transfer']['to'] == dst.address

def checkFailedTransfer(tok, src, dst, sender, amount, transferFunc):
    with brownie.reverts():
        tx = transferFunc(tok, src, dst, sender, amount)



@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


class GenericTokenTest:
    
    # Must override this function!
    # Returns a token instance
    def deploy_tok(self, account):
        return None 

    # Must override this function
    # returns a transaction receipt.
    def mint_funds(self, tok, account, amount):
        return None

    # def deploy_tok(self, price: int, maxtok: int) -> RUToken:
    #     return self.tokenType().deploy


    # def deploy_and_mint(self, price: int, maxtok: int, mintamount: int, mintaccount) -> RUToken:
    #     tok = self.deploy_tok(price, maxtok)
    #     tx = tok.mint(msg(mintaccount, amount=price*mintamount))
    #     return tok
    def deploy_and_mint(self, mintamount: int, mintaccount, tokaccount = None):
        if tokaccount is None:
            tokaccount = accounts.add()
            accounts[0].transfer(tokaccount, 1e10) # Give an initial balance
        tok = self.deploy_tok(tokaccount)
        tx = self.mint_funds(tok, mintaccount, mintamount)
        assert tok.balanceOf(mintaccount) == mintamount
        return tok


    # Test that a simple deployment works.
    def test_simple_deploy(self):
        tok = self.deploy_tok(accounts[0])




    def simple_transfer_testbody(self, txnum: int, extranum: int, a1, a2):
        totalmint = txnum + extranum

        # if a1 == a2:
        #     return # Transfer must be between different accounts.

        tok = self.deploy_and_mint(totalmint, a1)
        checkSuccessfulTransfer(tok, a1, a2, a1, txnum, transfer_direct)


    # Test simple transfer between two accounts.
    @given(
        txnum=strategy('uint', min_value=0, max_value=100),
        extranum=strategy('uint', min_value=1, max_value=100),
        a1=strategy('address'),
        a2=strategy('address'),
    )
    @settings(max_examples=15)
    def test_simple_transfer(self, txnum, extranum, a1, a2):
        self.simple_transfer_testbody(txnum, extranum, a1, a2)

    # Test successful zero transfer between two accounts.
    def test_zero_transfer(self):
        self.simple_transfer_testbody(0, 10, accounts[1], accounts[2])


    # Test failed transfer between two accounts.
    def test_insufficent_funds_transfer(self):
        totalmint = 500
        a1 = accounts[1]
        a2 = accounts[2]

        tok = self.deploy_and_mint(totalmint, a1)
        a1balance = tok.balanceOf(a1)
        
        checkFailedTransfer(tok, a1, a2, a1, a1balance + 1, transfer_direct)


    def deploy_mint_approve(self, totalmint: int, approveamount: int, a1, a2) -> RUToken:
        tok = self.deploy_and_mint(totalmint, a1)

        assert tok.balanceOf(a1) == totalmint

        orig_allowance = tok.allowance(a1, a2)
        assert orig_allowance == 0

        tx = tok.approve(a2, approveamount, {'from': a1})
        assert tx.return_value == True
        assert 'Approval' in tx.events
        assert tx.events['Approval']['owner'] == a1.address
        assert tx.events['Approval']['spender'] == a2.address
        assert tx.events['Approval']['value'] == approveamount

        new_allowance = tok.allowance(a1, a2)
        assert new_allowance == approveamount

        return tok

    def test_approve_transferFrom(self):
        totalmint = 500
        approveamount = 200
        transferamount = 100
        
        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(totalmint, approveamount, a1, a2)
        checkSuccessfulTransfer(tok, a1, a3, a2, transferamount, transfer_byproxy)



    def test_approve_multiple_transferFrom(self):
        transferamount = 100
        totalmint = transferamount * 4
        approveamount = totalmint + 10
        
        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(totalmint, approveamount, a1, a2)
        checkSuccessfulTransfer(tok, a1, a3, a2, transferamount, transfer_byproxy)
        checkSuccessfulTransfer(tok, a1, a3, a2, transferamount * 2, transfer_byproxy)
        checkSuccessfulTransfer(tok, a1, a3, a2, transferamount - 10, transfer_byproxy)

        
    def test_notapproved_transferFrom(self):
        totalmint = 500
        approveamount = 200
        transferamount = 100
        
        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]
        a4 = accounts[4]

        tok = self.deploy_mint_approve(totalmint, approveamount, a1, a2)
        checkFailedTransfer(tok, a1, a3, a4, transferamount, transfer_byproxy)


    def test_insufficient_allowance_transferFrom(self):
        totalmint = 500
        approveamount = 200
        
        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(totalmint, approveamount, a1, a2)
        checkFailedTransfer(tok, a1, a3, a2, approveamount + 1, transfer_byproxy)


    def test_insufficient_allowance_multiple_transferFrom(self):
        totalmint = 500
        approveamount = 200
        
        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(totalmint, approveamount, a1, a2)
        checkSuccessfulTransfer(tok, a1, a3, a2, approveamount - 10, transfer_byproxy)
        checkFailedTransfer(tok, a1, a3, a2, 15, transfer_byproxy)


    def test_insufficient_funds_transferFrom(self):
        totalmint = 500
        approveamount = 600
        
        a1 = accounts[1]
        a2 = accounts[2]
        a3 = accounts[3]

        tok = self.deploy_mint_approve(totalmint, approveamount, a1, a2)
        checkFailedTransfer(tok, a1, a3, a2, approveamount, transfer_byproxy)


@pytest.fixture(autouse=True, scope='class')
def default_setup(request):
    request.cls.price = 100
    request.cls.maxtok = 1000


def deploy_ru_token(price, maxtok, account):
    return RUToken.deploy(price, maxtok, msg(account))

def mint_ru_tokens(tok, account, amount):
    price = tok.tokenPrice()
    return tok.mint(msg(account, amount * price))

class TestRUToken(GenericTokenTest):

    # Must override this function!
    # Returns a token instance
    def deploy_tok(self, account):
        return deploy_ru_token(self.price, self.maxtok, account)

    # Must override this function
    # returns a transaction receipt.
    def mint_funds(self, tok: RUToken, account, amount):
        return mint_ru_tokens(tok, account, amount)


    # Test mint-burn sequence from single address
    @given(
        price=sampled_from([100, 3, 22]),
        txnum=strategy('uint', min_value=1, max_value=100),
        extranum=strategy('uint', min_value=0, max_value=100),
    )
    @settings(max_examples=20)
    def test_mint_burn(self, price, txnum, extranum):
        self.price = price
        totalmint = txnum + extranum
        self.maxtok = totalmint

        a1 = accounts[1]

        tok = self.deploy_tok(accounts[0])
        tx1 = self.mint_funds(tok, a1, totalmint)

        orig_eth_balance = a1.balance()
        tx2 = tok.burn(txnum, msg(a1))
        new_token_balance = tok.balanceOf(a1, msg(0))
        new_eth_balance = a1.balance()
        assert new_token_balance == extranum
        assert new_eth_balance == orig_eth_balance + txnum * price



    # Test mint-burn-insufficient 
    @given(
        price=sampled_from([100, 3, 22]),
        maxtok=strategy('uint', min_value=1, max_value=100),
    )
    @settings(max_examples=20)
    def test_mint_burn_insufficient(self, price, maxtok):
        self.price = price
        self.maxtok = maxtok
        maxnum = 1000

        a1 = accounts[1]

        tok = self.deploy_tok(a1)
        tx1 = self.mint_funds(tok, a1, maxtok)

        orig_eth_balance = a1.balance()
        with brownie.reverts():
            tx2 = tok.burn(maxtok + 1, msg(a1))


    # Test mint-transfer-burn sequence.
    @given(
        price=sampled_from([100, 3, 22]),
        txnum=strategy('uint', min_value=1, max_value=100),
        extranum=strategy('uint', min_value=0, max_value=100),
    )
    @settings(max_examples=20)
    def test_mint_transfer_burn(self, price, txnum, extranum):
        self.price = price
        self.maxtok = 1000

        a1 = accounts[1]
        a2 = accounts[2]

        totalmint = txnum + extranum

        if a1 == a2:
            return # Transfer must be between different accounts.

        tok = self.deploy_tok(accounts[0])
        tx1 = self.mint_funds(tok, a1, totalmint)
        checkSuccessfulTransfer(tok, a1, a2, a1, txnum, transfer_direct)

        orig_eth_balance = a2.balance()
        tx3 = tok.burn(txnum, msg(a2))
        new_token_balance = tok.balanceOf(a2, msg(0))
        new_eth_balance = a2.balance()
        assert new_token_balance == 0
        assert new_eth_balance == orig_eth_balance + txnum * price

    
    # Test that a single minting call works
    @given(
        price=strategy('uint', min_value=1, max_value=1000), 
        num=strategy('uint', min_value=1, max_value=100),
        to=strategy('address'),
    )
    @settings(max_examples=15)
    def test_single_mint(self, price, num, to):
        self.price = price
        self.maxtok = 100
        tok = self.deploy_tok(accounts[0])
        orig_supply = tok.totalSupply()
        assert orig_supply == 0

        orig_token_balance = tok.balanceOf(to, msg(0))
        orig_eth_balance = to.balance()
        assert orig_token_balance == 0 

        tx = self.mint_funds(tok, to, num)

        new_supply = tok.totalSupply()
        assert new_supply == num

        new_token_balance = tok.balanceOf(to, msg(0))
        new_eth_balance = to.balance()
        assert new_token_balance == num
        assert new_eth_balance <= orig_eth_balance - price*num


    # Check that the maximum token amount is observed
    def test_max_mint_single(self):
        self.price = 100
        self.maxtok = 10
        to = accounts[1]

        tok = self.deploy_tok(accounts[0])
        with brownie.reverts():
            tx = tok.mint(msg(to, amount=self.price*(self.maxtok + 1)))

    # Check that maximum token amount is observed when minting in two phases
    def test_max_mint_double_same(self):
        self.price = 100
        self.maxtok = 10
        to = accounts[1]

        tok = self.deploy_and_mint(self.maxtok, to)

        with brownie.reverts():
            tx = self.mint_funds(tok, to, 1)

    # Check that maximum token amount is observed when minting in two phases with different addresses.
    def test_max_mint_double_different(self):
        self.price = 100
        self.maxtok = 10
        to1 = accounts[1]
        to2 = accounts[2]

        tok = self.deploy_and_mint(self.maxtok, to1)

        with brownie.reverts():
            tx = self.mint_funds(tok, to2, 1)


import unittest
import numpy as np
import pandas as pd
from abacus_bhishma.ema_cloud import aggregate_minutes, add_features, expected_minutes


def minutes(start='2018-01-02 14:30', n=15):
    ts = pd.date_range(start, periods=n, freq='min', tz='UTC')
    return pd.DataFrame(dict(timestamp=ts, contract=['ES:A']*n,
                             open=np.arange(n)+100., high=np.arange(n)+102.,
                             low=np.arange(n)+99., close=np.arange(n)+101., volume=np.ones(n)))


def schedule(source):
    return pd.DataFrame(dict(timestamp=source.timestamp, session=['2018-01-02']*len(source),
                             calendar_event=['']*len(source), calendar_valid=[True]*len(source)))


class AggregationTests(unittest.TestCase):
    def test_independent_three_and_five_half_open(self):
        src = minutes()
        three = aggregate_minutes(src, 3, schedule(src), 'ES')
        five = aggregate_minutes(src, 5, schedule(src), 'ES')
        self.assertEqual(list(three.close), [103.,106.,109.,112.,115.])
        self.assertEqual(list(five.close), [105.,110.,115.])
        self.assertEqual(three.high.iloc[0],104.)
        self.assertEqual(three.low.iloc[0],99.)
        self.assertEqual(three.volume.sum(),15.)
        self.assertEqual(three.available_at.iloc[0],src.timestamp.iloc[3])
        self.assertTrue(three.usable.all())

    def test_partial_empty_and_no_fill(self):
        src=minutes(); roster=schedule(src)
        src=src.drop(index=[1,5,6,7,8,9])
        bars=aggregate_minutes(src,5,roster,'ES')
        self.assertEqual(len(bars),3)
        self.assertEqual(bars.missing_offsets.iloc[0],'1')
        self.assertFalse(bars.usable.iloc[0])
        self.assertEqual(bars.source_count.iloc[1],0)
        self.assertTrue(pd.isna(bars.close.iloc[1]))
        self.assertTrue(pd.isna(bars.volume.iloc[1]))
        self.assertTrue(bars.usable.iloc[2])

    def test_mixed_contract_and_duplicate(self):
        src=minutes(); roster=schedule(src);src.loc[2,'contract']='ES:B'
        src=pd.concat([src.iloc[:2],src.iloc[[1]],src.iloc[2:]],ignore_index=True)
        bars=aggregate_minutes(src,5,roster,'ES')
        self.assertFalse(bars.usable.iloc[0]);self.assertIsNone(bars.contract.iloc[0])
        self.assertIn('mixed_contract',bars.quality_reason.iloc[0])
        self.assertIn('duplicate_source_minute',bars.quality_reason.iloc[0])

    def test_missing_contract_identity_is_never_usable(self):
        src=minutes();roster=schedule(src)
        src.loc[:4,'contract']=None
        src.loc[6,'contract']=None
        src.loc[11,'contract']=''
        bars=aggregate_minutes(src,5,roster,'ES')
        self.assertFalse(bars.usable.any())
        self.assertEqual(bars.contract_count.iloc[0],0)
        self.assertTrue(bars.quality_reason.str.contains('missing_contract_identity').all())
        self.assertEqual(bars.contract.iloc[1],'ES:A')

    def test_invalid_ohlc_and_calendar_remain_records(self):
        src=minutes();roster=schedule(src);src.loc[1,'high']=1.;roster.loc[5:9,'calendar_valid']=False
        bars=aggregate_minutes(src,5,roster,'GC')
        self.assertFalse(bars.usable.iloc[0]);self.assertFalse(bars.usable.iloc[1])
        self.assertIn('invalid_source_ohlcv',bars.quality_reason.iloc[0])
        self.assertIn('calendar_uncertified',bars.quality_reason.iloc[1])

    def test_pause_dst_and_holiday(self):
        for start,end in [('2018-03-09','2018-03-13'),('2018-11-02','2018-11-06')]:
            roster=expected_minutes('ES',start,end)
            local=roster.timestamp.dt.tz_convert('America/New_York')
            self.assertFalse(((local.dt.hour==16)&local.dt.minute.between(15,29)).any())
            self.assertEqual(roster.groupby('session').size().tolist(),[1365,1365])
            offsets={x.utcoffset().total_seconds() for x in local}
            self.assertEqual(offsets,{-18000.,-14400.})
        holiday=expected_minutes('GC','2018-12-24','2018-12-26')
        self.assertFalse(holiday.calendar_valid.any())
        self.assertEqual(len(holiday),2760)


class FeatureTests(unittest.TestCase):
    def bars(self,n=505):
        src=minutes(n=n*5)
        return aggregate_minutes(src,5,schedule(src),'ES')

    def test_first_close_seed_and_wilder_seed(self):
        bars=self.bars(16);got=add_features(bars,warmup=14)
        expected20=bars.close.iloc[0];expected50=expected20;trs=[];prev=None
        for i,row in bars.iterrows():
            expected20=row.close if i==0 else 2/21*row.close+19/21*expected20
            expected50=row.close if i==0 else 2/51*row.close+49/51*expected50
            trs.append(row.high-row.low if prev is None else max(row.high-row.low,abs(row.high-prev),abs(row.low-prev)))
            self.assertAlmostEqual(got.ema20.iloc[i],expected20)
            self.assertAlmostEqual(got.ema50.iloc[i],expected50);prev=row.close
        self.assertTrue(pd.isna(got.atr14.iloc[12]))
        self.assertAlmostEqual(got.atr14.iloc[13],sum(trs[:14])/14)
        self.assertAlmostEqual(got.atr14.iloc[14],(13*got.atr14.iloc[13]+trs[14])/14)

    def test_warmup_exactly_250_and_500_prefix_invariance(self):
        bars=self.bars();got=add_features(bars);more=add_features(bars,warmup=500)
        self.assertFalse(got.feature_valid.iloc[248]);self.assertTrue(got.feature_valid.iloc[249])
        self.assertFalse(more.feature_valid.iloc[498]);self.assertTrue(more.feature_valid.iloc[499])
        pd.testing.assert_frame_equal(got.iloc[:301].reset_index(drop=True),add_features(bars.iloc[:301]))
        np.testing.assert_allclose(got.ema50,more.ema50)

    def test_roll_unknown_missing_and_scheduled_closure(self):
        bars=self.bars(30);bars.loc[15:,'contract']='ES:B'
        got=add_features(bars,warmup=14)
        self.assertEqual(got.consecutive_count.iloc[15],1)
        self.assertEqual(got.feature_reset_reason.iloc[15],'contract_switch')
        bars=self.bars(30);bars.loc[10,'usable']=False;bars.loc[10,'quality_reason']='empty_bucket'
        got=add_features(bars,warmup=14)
        self.assertTrue(pd.isna(got.ema20.iloc[10]));self.assertEqual(got.consecutive_count.iloc[11],1)
        bars=self.bars(30);bars.loc[15:,'timestamp']+=pd.Timedelta(hours=1)
        bars.loc[15:,'available_at']+=pd.Timedelta(hours=1)
        got=add_features(bars,warmup=14);self.assertEqual(got.consecutive_count.iloc[15],1)
        bars.loc[15,'known_closure_before']=True
        got=add_features(bars,warmup=14);self.assertEqual(got.consecutive_count.iloc[15],16)
        self.assertFalse(got.feature_reset.iloc[15])


if __name__=='__main__':unittest.main()

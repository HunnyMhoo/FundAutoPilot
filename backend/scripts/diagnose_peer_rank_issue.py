"""
Diagnostic script to investigate why "Equity Large Cap" funds are not getting peer ranks.

Checks:
1. Funds with peer_key "Equity Large Cap"
2. Peer stats for "Equity Large Cap"
3. Fund identifiers and representative classes
4. Return data availability
"""

import sys
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, and_
from app.core.database import SyncSessionLocal
from app.models.fund_orm import Fund, FundReturnSnapshot, PeerStats
from app.services.representative_class_service import RepresentativeClassService
from app.services.peer_ranking_service import PeerRankingService
from app.services.peer_stats_service import PeerStatsService


def main():
    peer_key = "Equity Large Cap"
    
    print(f"=== Diagnosing Peer Rank Issue for '{peer_key}' ===\n")
    
    with SyncSessionLocal() as session:
        # 1. Check funds with this peer key
        print("1. Checking funds with peer_key = 'Equity Large Cap'...")
        funds_query = select(Fund).where(
            and_(
                Fund.peer_key == peer_key,
                Fund.fund_status == "RG"
            )
        )
        funds = list(session.execute(funds_query).scalars().all())
        print(f"   Found {len(funds)} active funds with this peer_key\n")
        
        if len(funds) == 0:
            print("   ❌ No funds found! Check if peer_key is set correctly.")
            return
        
        # Show sample funds
        print("   Sample funds:")
        for fund in funds[:5]:
            print(f"   - {fund.proj_id} | class: '{fund.class_abbr_name}' | name: {fund.fund_name_en[:50]}")
        if len(funds) > 5:
            print(f"   ... and {len(funds) - 5} more")
        print()
        
        # 2. Check peer stats
        print("2. Checking peer stats...")
        latest_date_query = (
            select(func.max(FundReturnSnapshot.as_of_date))
        )
        latest_date = session.execute(latest_date_query).scalar()
        
        if latest_date:
            print(f"   Latest snapshot date: {latest_date}")
            
            for horizon in ["1y", "ytd", "3y", "5y"]:
                stats_query = select(PeerStats).where(
                    and_(
                        PeerStats.peer_key == peer_key,
                        PeerStats.horizon == horizon,
                        PeerStats.as_of_date <= latest_date
                    )
                ).order_by(PeerStats.as_of_date.desc()).limit(1)
                
                stats = session.execute(stats_query).scalar_one_or_none()
                if stats:
                    print(f"   {horizon}: peer_count_total={stats.peer_count_total}, "
                          f"peer_count_eligible={stats.peer_count_eligible}, "
                          f"as_of_date={stats.as_of_date}")
                    if stats.peer_count_eligible < 10:
                        print(f"      ⚠️  Insufficient peers (< 10)")
                else:
                    print(f"   {horizon}: ❌ No peer stats found")
            print()
        else:
            print("   ❌ No return snapshots found in database")
            print()
        
        # 3. Check representative classes
        print("3. Checking representative classes...")
        proj_ids = list(set([f.proj_id for f in funds]))
        rep_class_service = RepresentativeClassService(session)
        rep_classes = rep_class_service.select_representative_classes_batch(proj_ids)
        
        print(f"   Checking {len(proj_ids)} unique proj_ids...")
        for proj_id in proj_ids[:5]:
            rep_class = rep_classes.get(proj_id)
            fund_classes = [f for f in funds if f.proj_id == proj_id]
            class_names = [f.class_abbr_name for f in fund_classes]
            print(f"   {proj_id}:")
            print(f"      Classes: {class_names}")
            print(f"      Representative: {rep_class}")
            
            # Determine identifier that would be used
            if rep_class:
                identifier = rep_class
            elif fund_classes[0].class_abbr_name:
                identifier = fund_classes[0].class_abbr_name
            else:
                identifier = proj_id
            print(f"      Identifier used: {identifier}")
        print()
        
        # 4. Test fund lookup
        print("4. Testing fund lookup with PeerRankingService...")
        ranking_service = PeerRankingService(session)
        
        # Test with a sample fund
        test_fund = funds[0]
        if rep_classes.get(test_fund.proj_id):
            test_identifier = rep_classes[test_fund.proj_id]
        elif test_fund.class_abbr_name:
            test_identifier = test_fund.class_abbr_name
        else:
            test_identifier = test_fund.proj_id
        
        print(f"   Testing with fund: {test_fund.proj_id}")
        print(f"   Using identifier: {test_identifier}")
        
        # Try to get fund
        found_fund = ranking_service._get_fund(test_identifier)
        if found_fund:
            print(f"   ✅ Fund found: {found_fund.proj_id} | class: '{found_fund.class_abbr_name}'")
            print(f"   Peer key: {found_fund.peer_key}")
            
            # Check return data
            if latest_date:
                for horizon in ["1y", "ytd"]:
                    fund_return = ranking_service._get_fund_return(
                        found_fund.proj_id,
                        found_fund.class_abbr_name,
                        horizon,
                        latest_date
                    )
                    if fund_return is not None:
                        print(f"   {horizon} return: {fund_return}")
                    else:
                        print(f"   {horizon} return: ❌ None")
        else:
            print(f"   ❌ Fund not found with identifier '{test_identifier}'")
        print()
        
        # 5. Test peer rank computation
        print("5. Testing peer rank computation...")
        if latest_date and found_fund:
            try:
                rank_result = ranking_service.compute_peer_rank(
                    test_identifier,
                    "1y",
                    latest_date
                )
                print(f"   Result:")
                print(f"      Percentile: {rank_result.percentile}")
                print(f"      Unavailable reason: {rank_result.unavailable_reason}")
                print(f"      Peer count eligible: {rank_result.peer_count_eligible}")
                print(f"      Peer key: {rank_result.peer_key}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        print()
        
        # 6. Check specific fund from the table (M0027_2535)
        print("6. Checking specific fund M0027_2535...")
        specific_fund_query = select(Fund).where(
            and_(
                Fund.proj_id == "M0027",
                Fund.class_abbr_name == "2535"
            )
        )
        specific_fund = session.execute(specific_fund_query).scalar_one_or_none()
        
        if specific_fund:
            print(f"   Found: {specific_fund.fund_name_en[:60]}")
            print(f"   Peer key: {specific_fund.peer_key}")
            print(f"   Class abbr name: '{specific_fund.class_abbr_name}'")
            
            # Check representative class
            rep_class = rep_classes.get(specific_fund.proj_id)
            print(f"   Representative class: {rep_class}")
            
            # Determine identifier
            if rep_class:
                identifier = rep_class
            elif specific_fund.class_abbr_name:
                identifier = specific_fund.class_abbr_name
            else:
                identifier = specific_fund.proj_id
            print(f"   Identifier would be: {identifier}")
            
            # Try lookup
            found = ranking_service._get_fund(identifier)
            if found:
                print(f"   ✅ Lookup successful")
                if latest_date:
                    rank_result = ranking_service.compute_peer_rank(
                        identifier,
                        "1y",
                        latest_date
                    )
                    print(f"   Peer rank result:")
                    print(f"      Percentile: {rank_result.percentile}")
                    print(f"      Reason: {rank_result.unavailable_reason}")
            else:
                print(f"   ❌ Lookup failed")
        else:
            print(f"   ❌ Fund not found (proj_id='M0027', class_abbr_name='2535')")
            # Try alternative lookup
            alt_query = select(Fund).where(Fund.proj_id.like("M0027%"))
            alt_funds = list(session.execute(alt_query).scalars().all())
            print(f"   Found {len(alt_funds)} funds with proj_id like 'M0027%':")
            for f in alt_funds[:3]:
                print(f"      {f.proj_id} | class: '{f.class_abbr_name}' | peer_key: {f.peer_key}")


if __name__ == "__main__":
    main()


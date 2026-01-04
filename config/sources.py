"""
Source configuration for news and social media scrapers.
"""
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class SourceType(str, Enum):
    """Types of content sources."""
    NEWS = "news"
    SOCIAL = "social"
    COUNCIL = "council"


class County(str, Enum):
    """Counties served by the newsletter."""
    NASH = "nash"
    EDGECOMBE = "edgecombe"
    WILSON = "wilson"


@dataclass
class NewsSource:
    """Configuration for a news website source."""
    name: str
    display_name: str
    url: str
    county: Optional[County]
    article_selector: str = "article"
    title_selector: str = "h1, h2, .headline"
    content_selector: str = ".article-content, .story-body, .entry-content"
    date_selector: str = ".date, time, .published"
    is_active: bool = True


@dataclass
class CouncilSource:
    """Configuration for a government council/meeting minutes source."""
    name: str
    display_name: str
    url: str
    county: County
    minutes_selector: str = "a[href*='minute'], a[href*='agenda'], .meeting-minutes"
    is_active: bool = True


@dataclass
class SocialSource:
    """Configuration for a social media source."""
    name: str
    display_name: str
    platform: str  # 'facebook' or 'instagram'
    account_id: str
    county: Optional[County]
    is_active: bool = True


# News Sources Configuration
NEWS_SOURCES: List[NewsSource] = [
    NewsSource(
        name="rocky_mount_telegram",
        display_name="Rocky Mount Telegram",
        url="https://www.rockymounttelegram.com",
        county=County.NASH,
    ),
    NewsSource(
        name="nashville_graphic",
        display_name="Nashville Graphic",
        url="https://www.nashvillegraphic.com",
        county=County.NASH,
    ),
    NewsSource(
        name="my_tarboro_today",
        display_name="My Tarboro Today",
        url="https://www.mytarborotoday.com",
        county=County.EDGECOMBE,
    ),
    NewsSource(
        name="spring_hope_enterprise",
        display_name="Spring Hope Enterprise",
        url="https://www.springhopeenterprise.com",
        county=County.NASH,
    ),
    NewsSource(
        name="wilson_times",
        display_name="Wilson Times",
        url="https://www.wilsontimes.com",
        county=County.WILSON,
    ),
    NewsSource(
        name="nash_county_economic_dev",
        display_name="Nash County Economic Development",
        url="https://www.nashcountync.gov/departments/economic_development/index.php",
        county=County.NASH,
    ),
    NewsSource(
        name="carolinas_gateway",
        display_name="Carolina's Gateway Partnership",
        url="https://www.carolinasgateway.com/news",
        county=None,  # Regional
    ),
]


# Council/Government Meeting Minutes Sources
COUNCIL_SOURCES: List[CouncilSource] = [
    CouncilSource(
        name="tarboro_council",
        display_name="Town of Tarboro - Town Council",
        url="https://www.tarboro-nc.com/government/town_council/agendas_and_minutes.php",
        county=County.EDGECOMBE,
    ),
    CouncilSource(
        name="rocky_mount_council",
        display_name="City of Rocky Mount - City Council",
        url="https://www.rockymountnc.gov/city_council_meetings",
        county=County.NASH,
    ),
    CouncilSource(
        name="nashville_council",
        display_name="Town of Nashville - Town Council",
        url="https://www.townofnashville.com/government/town-council",
        county=County.NASH,
    ),
    CouncilSource(
        name="spring_hope_council",
        display_name="Town of Spring Hope - Town Board",
        url="https://www.springhopenc.com/town-board",
        county=County.NASH,
    ),
    CouncilSource(
        name="nash_county_commissioners",
        display_name="Nash County Board of Commissioners",
        url="https://www.nashcountync.gov/departments/board_of_commissioners/index.php",
        county=County.NASH,
    ),
    CouncilSource(
        name="edgecombe_county_commissioners",
        display_name="Edgecombe County Board of Commissioners",
        url="https://www.edgecombecountync.gov/government/board_of_commissioners/index.php",
        county=County.EDGECOMBE,
    ),
]


# Social Media Sources - Local Restaurants and Bars
RESTAURANT_SOCIAL_SOURCES: List[SocialSource] = [
    SocialSource("lou_redas", "Lou Reda's", "facebook", "LouRedasRockyMount", County.NASH),
    SocialSource("lilyanns", "Lilyann's", "facebook", "LilyannsRM", County.NASH),
    SocialSource("goat_island", "Goat Island Bottle Shop", "facebook", "goatislandbottleshop", County.NASH),
    SocialSource("prime_smokehouse", "Prime Smokehouse", "facebook", "primesmokehouse", County.NASH),
    SocialSource("hopfly_brewery", "Hopfly Brewing Company", "facebook", "hopflybrewing", County.NASH),
    SocialSource("lazeez", "Lazeez Mediterranean", "facebook", "LazeezRockyMount", County.NASH),
    SocialSource("saigon_on_main", "Saigon on Main", "facebook", "SaigonOnMain", County.NASH),
    SocialSource("on_the_square", "On the Square", "facebook", "OnTheSquareRM", County.NASH),
    SocialSource("boars_head_brewery", "Boar's Head Brewery", "facebook", "BoarsHeadBrewery", County.NASH),
]


# Social Media Sources - Community Partners
COMMUNITY_SOCIAL_SOURCES: List[SocialSource] = [
    SocialSource("rm_chamber", "Rocky Mount Area Chamber of Commerce", "facebook", "RockyMountChamber", County.NASH),
    SocialSource("clair_de_lune", "Clair De Lune", "facebook", "ClairDeLuneRM", County.NASH),
    SocialSource("ripe_for_revival", "Ripe for Revival", "facebook", "RipeForRevival", County.NASH),
    SocialSource("stifel", "Stifel", "facebook", "Stifel", County.NASH),
    SocialSource("metro_maintenance", "Metro Maintenance", "facebook", "MetroMaintenanceNC", County.NASH),
    SocialSource("simmons_harris", "Simmons & Harris, Inc.", "facebook", "SimmonsHarrisInc", County.NASH),
    SocialSource("landmark_financial", "Landmark Financial Services", "facebook", "LandmarkFinancialServices", County.NASH),
    SocialSource("braswell_farms", "Braswell Family Farms", "facebook", "BraswellFamilyFarms", County.NASH),
    SocialSource("hunt_gorham", "Hunt Hunt & Gorham", "facebook", "HuntHuntGorham", County.NASH),
    SocialSource("dunn_center", "Dunn Center for the Performing Arts", "facebook", "DunnCenter", County.NASH),
    SocialSource("elite_overhead", "Elite Overhead Garage Doors", "facebook", "EliteOverheadGarageDoors", County.NASH),
    SocialSource("baileys_jewelry", "Bailey's Fine Jewelry", "facebook", "BaileysFineJewelry", County.NASH),
    SocialSource("nash_cc", "Nash Community College", "facebook", "NashCC", County.NASH),
    SocialSource("essential_health", "Essential Health Medispa", "facebook", "EssentialHealthMedispa", County.NASH),
    SocialSource("rm_farmers_market", "Rocky Mount Farmers Market", "facebook", "RockyMountFarmersMarket", County.NASH),
    SocialSource("nutradrip", "NUTRADRiP", "facebook", "NUTRADRiP", County.NASH),
    SocialSource("franklin_hba", "Franklin County HBA", "facebook", "FranklinCountyHBA", County.NASH),
    SocialSource("southern_bank", "Southern Bank", "facebook", "SouthernBankNC", County.NASH),
    SocialSource("aaa_storage", "AAA Storage / Wellongate Apartments", "facebook", "AAAStorageWellongate", County.NASH),
    SocialSource("poyner_spruill", "Poyner Spruill LLP", "facebook", "PoynerSpruill", County.NASH),
    SocialSource("rm_medical_pharmacy", "Rocky Mount Medical Park Pharmacy", "facebook", "RMMedicalParkPharmacy", County.NASH),
    SocialSource("foote_real_estate", "Foote Real Estate Group", "facebook", "FooteRealEstateGroup", County.NASH),
    SocialSource("triangle_risk", "Triangle Risk Advisors", "facebook", "TriangleRiskAdvisors", County.NASH),
    SocialSource("unc_health_nash", "UNC Health Nash", "facebook", "UNCHealthNash", County.NASH),
    SocialSource("wildwood_lamps", "Wildwood Lamps", "facebook", "WildwoodLamps", County.NASH),
]


# Combined list of all social sources
ALL_SOCIAL_SOURCES: List[SocialSource] = RESTAURANT_SOCIAL_SOURCES + COMMUNITY_SOCIAL_SOURCES


def get_active_news_sources() -> List[NewsSource]:
    """Get all active news sources."""
    return [s for s in NEWS_SOURCES if s.is_active]


def get_active_council_sources() -> List[CouncilSource]:
    """Get all active council/government sources."""
    return [s for s in COUNCIL_SOURCES if s.is_active]


def get_active_social_sources() -> List[SocialSource]:
    """Get all active social media sources."""
    return [s for s in ALL_SOCIAL_SOURCES if s.is_active]


def get_sources_by_county(county: County) -> dict:
    """Get all sources for a specific county."""
    return {
        "news": [s for s in NEWS_SOURCES if s.county == county and s.is_active],
        "council": [s for s in COUNCIL_SOURCES if s.county == county and s.is_active],
        "social": [s for s in ALL_SOCIAL_SOURCES if s.county == county and s.is_active],
    }

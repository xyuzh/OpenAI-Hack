from workflow.core.config.app_config import AppConfig
from workflow.service.exa import ExaService
from workflow.tool.web_search.tool import WebSearchParam, WebSearchType

async def web_crawl_executor(search_param: WebSearchParam, exa: ExaService) -> str:
    match search_param.type:
        case WebSearchType.SEARCH:
            res = await exa.search(search_param.query)
       
        case WebSearchType.CRAWL:
            res = await exa.crawl(search_param.query)
    output = "\n\n".join(str(result) for result in res.results)
    return output
    

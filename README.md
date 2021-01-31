基金助手 Fund Assistant
=======

以Interactive shell形式收集国内基金数据的小工具。
可以通过谷歌新闻搜索和谷歌自然语言API的情感分析来预测基金净值走势。

声明和已知问题:
--------

- 此工具暂时不支持国外基金。
- 基金净值预测算法所用到的数据主要是基于从Google News上搜索到的有关各个股票的文章，
因此并不能保证文章内容的准确性。因此，请把这个工具单纯当做一个数据整合助手，请不要把
程序给出的预测当做加仓或者减仓的依据。判断一个基金未来的走势还是要靠自己的谨慎分析。
- 新闻内容的抓取用的是`newspaper`和`Goose`这两个库，在少数情况下新闻的主题会无法解析。

使用前提
--------
- 输入`pip install -r requirements`安装所有需要的packages。
- 如果在国内使用，确保能通过代理连接到谷歌。想要链接谷歌自然语言处理的API首先要申请获得API key，
然后把API key加进环境变量。具体方法可以参考以下链接：

    - [Windows终端命令行下如何使用代理](https://github.com/shadowsocks/shadowsocks-windows/issues/1489)
    - [Using API Keys](https://cloud.google.com/docs/authentication/api-keys) 

- 在FundAssistant开始运行之前，会先测试网络链接，如果出现问题会有提示信息。只有当
链接谷歌服务的时候没有报错，工具中的`predict`功能才能正常使用。其他和基金有关的信息（比如历史净值）
的获取不需要用到谷歌。

使用方法和主要功能
--------
- 所有指令的具体用法请在开始程序后用`help`加上指令名进行查看。比如：
```
fund-assistant> help fund
> fund info      : prints all information on the current fund
> fund code      : prints the fund code
> fund name      : prints the name of the current fund
> fund nav       : prints the net asset value of the fund in the past month
> fund nav <int> : prints the net asset value of the fund of the past <int> months
> fund cnv       : prints the cumulative net value of the fund in the past month
> fund cnv <int> : prints the cumulative net value of the fund in the past <int> months
> fund dy        : prints the daily yield of the fund in the past month
> fund dy <int>  : prints the daily yield value of the fund in the past <int> months
> fund stocks    : prints the stock positions of the current fund
> fund yields    : prints the yields of the fund in 1 year, 6 months, 3 months and 1 month
> fund prediction: prints the contribution of each stock to the overall prediction of the fund
```

- 进入工具后先输入`set`加上基金代码来选定想要查看的基金。成功后会显示
`Current fund set to <基金名称> (<基金代码>)` 。之后可以通过`fund`指令来查看
收集到的和当前基金有关的数据，比如：
```
fund-assistant (161725)> fund stocks  # 显示当前基金持仓
Stock positions:
+--------+----------+-------+
|  Code  |   Name   | Ratio |
+--------+----------+-------+
| 600809 | 山西汾酒 | 15.23 |
| 000568 | 泸州老窖 | 14.71 |
| 002304 | 洋河股份 | 13.62 |
| 000858 | 五 粮 液 | 12.89 |
| 600519 | 贵州茅台 | 12.67 |
| 000799 |  酒鬼酒  |  4.58 |
| 603369 |  今世缘  |  4.03 |
| 000860 | 顺鑫农业 |  3.82 |
| 000596 | 古井贡酒 |  3.25 |
| 603589 |  口子窖  |  2.65 |
+--------+----------+-------+
```
- 历史单位净值和累计净值以及日增长率的图表可以通过`plot`指令来生成。

- 输入`param`指令来调整净值预测时所用到的参数。目前可以调整的参数有三个：
    - `n`：谷歌搜索新闻时返回的文章个数
    - `d`：谷歌搜索的时间范围
    - `v`：是否在执行预测指令时输出所有细节

- 可以用`predict`指令加上股票代码或者股票名称对持仓的某一个股票单独使用来预测它的涨跌。
整个基金单位净值的预测可以通过运行`predict all`来实现。例子如下：
```
fund-assistant (161725)> predict 002304
Analysis will be run with the following parameters:
num_results: 10
date_range : Past week
verbose    : False
洋河股份: 100%|█████████████████████████████████████████████████████| 10/10 [00:12<00:00,  1.27s/it]
Obtained sentiment analysis for information gathered on 洋河股份: (score: 0.1, magnitude: 32.5)
Total number links crawled: 10
Number of failed links: 0
```

- 谷歌搜索时所有收集到的文章可以用`article`指令查看，也可以直接在`logs/articles.log.json`中浏览。

- 日志信息可以通过`log print`指令来查看。

所有指令和解释
```
> fund info      : prints all information on the current fund
> fund code      : prints the fund code
> fund name      : prints the name of the current fund
> fund nav       : prints the net asset value of the fund in the past month
> fund nav <int> : prints the net asset value of the fund of the past <int> months
> fund cnv       : prints the cumulative net value of the fund in the past month
> fund cnv <int> : prints the cumulative net value of the fund in the past <int> months
> fund dy        : prints the daily yield of the fund in the past month
> fund dy <int>  : prints the daily yield value of the fund in the past <int> months
> fund stocks    : prints the stock positions of the current fund
> fund yields    : prints the yields of the fund in 1 year, 6 months, 3 months and 1 month
> fund prediction: prints the contribution of each stock to the overall prediction of the fund

> plot <options>      : plots the any combination of the three metrics nav, cnv, and dy for the current fund
                        in the past month. Note that metrics must be separated with spaces.
                        i.e. 'plot nav', 'plot nav cnv', 'plot nav cnv dy'
> plot <options> <int>: performs the same plotting action as 'plot <options>'. The only difference is
                        <int> specifies that data will be selected from the previous <int> months.

> param show          : displays the values of the parameters in use
> param n <int>       : sets the num_results parameter to <int>
> param d <date_range>: sets the date_range parameter to be <date_range>. <date_range> can only be one of
                        letters in the list ['h', 'd', 'w', 'm', 'y']
> param v             : toggles the value of the verbose parameter. If verbose is True, it will set to
                        False after this command is executed, and vice versa.

> predict all         : performs an aggregate analysis to predict the trend of the net asset value of the fund
> predict <stock_code>: predicts the trend of the value of the stock given by <stock_code>
> predict <stock_name>: predicts the trend of the value of the stock given by <stock_name>

> article view <int>       : print out the content of the article which has the index specified by <int>
> article list all         : lists the title and url of all the cached articles during analysis
> article list <stock_name>: lists the title and url of cached articles on the stock specified by <stock_name>
> article clear            : clears all the cached news articles

> log clear      : clears all the log entries
> log print all  : prints all the content in the log (use with caution as the size of the log might be large)
> log print <int>: prints the last <int> of lines of the log file

> clear: clears the console

> exit: exit the application
```

参考代码：
- [用Python获取基金历史净值数据](https://blog.csdn.net/FrankieHello/article/details/107777130)
""" Run `ContractorFinder` with `TERMS` """
from ContractorFinder import ContractorFinder

# TODO: move this to an .env file
TERMS: list[str] = ["Pennsylvania residential contractor"]

if __name__ == '__main__':
    finder = ContractorFinder()
    finder(TERMS)
    print(finder.contractors)

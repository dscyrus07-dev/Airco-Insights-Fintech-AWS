from app.services.banks._shared.generic_bank import GenericTransactionValidator, GenericValidationError


UnionValidationError = GenericValidationError


class UnionTransactionValidator(GenericTransactionValidator):
    pass


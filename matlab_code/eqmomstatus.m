function flags = eqmomstatus( status )
% Function converting the status logical array returned by EQMOM solvers
% into a structure of flags indicating the state of convergence.
%
% >> flags = eqmomstatus( code )
%   *Inputs :
%      + status: Status code about convergence    (1*16)[logical]
%   *Outputs :
%      + flags : Structure of convergence flags   (1*1)[struct]
%
% == LIST OF FLAGS AND MEANINGS ==
% * wrongInputFormat:        Vector of moment is badly defined (wrong size, non
%                          numerical values, non real values, non finite values
%                          or NaN values). If true, all outputs are set to NaN.
% * nullSigma:               The returned sigma value is null. Implies that
%                          optimisations are possible by replacing nested
%                          quadrature by a direct quadrature using the weights
%                          and nodes from EQMOM solver.
% * nullWeight:              At least one weight is negative.
% * nullAbscicca:            One main node is located in 0. Can be an issue
%                          for kernels whose location parameter should not be 0.
% * nonRealisableInputs:     Raw vector of moment is not realisable. Current
%                          implementations return NaN values if this flag is
%                          enabled. Future implementations will still perform
%                          a reconstruction if at least the 3 first moments
%                          are realisable in order to max out the number of
%                          preserved moments.
% * maxEvalReached:          The iterative procedure stopped due to the maximum
%                          number of tested sigma values beoing reached. The
%                          yielded quadrature should not be considered as
%                          accurate.
% * convergedOnCriteria:     The iterative procedure stopped after a root of
%                          the objective function was found or because
%                          analytical solutions were used.
% * convergedOnInterval:     The search interval for sigma reached small enough
%                          size to consider the iterative procedure converged,
%                          or analytical solutions were used.
% * allMomentsPreserved:     Indicates whether all moments are preserved by the
%                          quadrature. May be erroneous if option
%                          "checkMomentPreserved" was not activated.
% * trustMomentsPreserved:   Indicated whether the flag "allMomentsPreserved"
%                          should be trusted or if it might be erroneous.

% == Default option code ==
flags = struct('wrongInputFormat',          false,...
  'nullSigma',              false,...
  'nullWeight',             false,...
  'nullAbscicca',           false,...
  'nonRealisableInputs',    false,...
  'maxEvalReached',         false,...
  'convergedOnCriteria',    false,...
  'convergedOnInterval',    false,...
  'allMomentsPreserved',    false,...
  'trustMomentsPreserved',  false);

% == Read status code ==
for i=1:10
  if status(i)
    switch i
      case 1 , flags.wrongInputFormat           = true;
      case 2 , flags.nullSigma                  = true;
      case 3 , flags.nullWeight                 = true;
      case 4 , flags.nullAbscicca               = true;
      case 5 , flags.nonRealisableInputs        = true;
      case 6 , flags.maxEvalReached             = true;
      case 7 , flags.convergedOnCriteria        = true;
      case 8 , flags.convergedOnInterval        = true;
      case 9 , flags.allMomentsPreserved        = true;
      case 10, flags.trustMomentsPreserved      = true;
    end
  end
end

end


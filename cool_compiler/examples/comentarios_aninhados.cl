(* Comentario de bloco simples. *)

(*
   Comentario de bloco
   que ocupa varias linhas.
*)

(* Comentario com (* um nivel aninhado *) dentro dele. *)

(* Tres niveis: (* nivel 2 (* nivel 3 *) ainda nivel 2 *) de volta ao nivel 1 *)

class ComentariosAninhados {
    x : Int <- 1; -- comentario de linha depois de codigo valido

    -- Comentario de linha sozinho, numa linha inteira.

    y : Int <- 2;
};

-- Todo programa COOL precisa de uma classe Main com um metodo main(): e por
-- ali que a execucao comeca, e a fase semantica reclama se ela faltar.
class Main {
    main() : Object { new ComentariosAninhados };
};
